import random
from time import sleep
from threading import Thread
from queue import SimpleQueue, Empty
from typing import Tuple, Any, List, Dict

import cv2
import numpy as np

WINDOW_NAME = "Processed Video"
VIDEO_PATH = "C:/Users/ism/Videos/2024-07-21 21-17-45.mp4"


class Filter:
    def __init__(self):
        """
        Initialize filter.
        """
        self.input = SimpleQueue()
        self.outputs = []
        self.thread = None
        # simple boolean is not harmful in this threading scenario
        self.should_stop = False

    def setOutputs(self, outputs: List[SimpleQueue[Any]]):
        """
        Set output queues.
        :param outputs: list of queues.
        :return:
        """
        self.outputs = outputs

    def start(self):
        """
        Start filter process. Cannot be called while already running.
        :return:
        """
        self.should_stop = False
        if self.thread is not None and self.thread.is_alive():
            raise Exception("The filter is already running!")
        self.thread = Thread(target=self._runner)
        self.thread.start()

    def isRunning(self) -> bool:
        """
        Check if filter is running.
        :return: True or False.
        """
        return self.thread.is_alive()

    def stop(self):
        """
        Stop filter process.
        :return:
        """
        self.should_stop = True
        if self.thread is not None:
            self.thread.join()
        self.thread = None

    def _runner(self):
        """
        Function which runs in the filter process
        and invokes process function when data is passed in.
        :return:
        """
        while not self.should_stop:
            try:
                data = self.input.get(block=True, timeout=0.1)
            except Empty:
                continue

            if not self.process(data):
                self.should_stop = True
                break

    def process(self, data: Any) -> bool:
        """
        Base process function that passes data onto next filter.
        Must be called at the end of all derived process functions.
        :param data: Any data to process.
        :return: Bool whether a filter should continue running.
        """
        for output in self.outputs:
            output.put(data)
        return True


class Pipeline:
    """
    Pipeline aggregates filters and connects them with queues
    as specified by string notation.
    """
    def __init__(self, pipeline: Dict[str, Tuple[Filter, List[str]]]):
        """
        Initialize pipeline.
        :param pipeline: dict with names of filters as keys
        and tuples of (filter, list of output names) as values.
        Output names represent other filters and if unique
        - a brand-new output queue that can be accessed by getSource.
        """
        self.pipeline = pipeline
        self.outputs = {}
        for f, out in self.pipeline.values():
            outputs: List[SimpleQueue[Any]|None] = [None] * len(out)
            for i, el in enumerate(out):
                if el not in self.pipeline:
                    self.outputs[el] = SimpleQueue()
                    outputs[i] = self.outputs[el]
                else:
                    outputs[i] = self.pipeline[el][0].input
            f.setOutputs(outputs)

    def start(self):
        """
        Start pipeline.
        :return:
        """
        for f, _ in self.pipeline.values():
            f.start()

    def isRunning(self, fil: str) -> bool:
        """
        Check if pipeline is running.
        :param fil: filter name.
        :return: True if pipeline is running.
        """
        return self.pipeline[fil][0].isRunning()

    def stop(self):
        """
        Stop pipeline.
        :return:
        """
        for f, _ in self.pipeline.values():
            f.stop()

    def getSource(self, key: str) -> SimpleQueue[Any]:
        """
        Get predefined (by unique outputs) source by name.
        :param key: name of the output.
        :return: queue.
        """
        return self.outputs[key]

    def getSink(self, fil: str) -> SimpleQueue[Any]:
        """
        Get input queue of the filter.
        :param fil: filter name.
        :return: queue.
        """
        return self.pipeline[fil][0].input


class PinkFilter(Filter):
    def __init__(self):
        super().__init__()

    def process(self, frame):
        pink_frame = frame.copy()
        pink_frame[:, :, 2] = np.minimum(frame[:, :, 2] + 100, 255)
        return super().process(pink_frame)


class ShakingFilter(Filter):
    def __init__(self):
        super().__init__()

    def process(self, frame):
        rows, cols, _ = frame.shape
        shake_frame = frame.copy()
        max_shift = 10
        dx = random.randint(-max_shift, max_shift)
        dy = random.randint(-max_shift, max_shift)

        M = np.float32([[1, 0, dx], [0, 1, dy]])
        shake_frame = cv2.warpAffine(shake_frame, M, (cols, rows))
        return super().process(shake_frame)


class HeartEffectFilter(Filter):
    def __init__(self):
        super().__init__()

    def process(self, frame):
        heart_frame = frame.copy()
        center_x, center_y = frame.shape[1] // 2, frame.shape[0] // 2
        radius = 40
        cv2.circle(heart_frame, (center_x - radius, center_y - radius), radius, (0, 0, 255), -1)
        cv2.circle(heart_frame, (center_x + radius, center_y - radius), radius, (0, 0, 255), -1)
        center_y += 2
        points = np.array([[center_x - 2 * radius - 2.5, center_y - radius],
                           [center_x + 2 * radius + 2.5, center_y - radius],
                           [center_x, center_y + radius * 2]], np.int32)
        cv2.fillPoly(heart_frame, [points], (0, 0, 255))

        return super().process(heart_frame)


class MirrorEffectFilter(Filter):
    def __init__(self):
        super().__init__()

    def process(self, frame):
        mirrored_frame = cv2.flip(frame, 1)
        return super().process(mirrored_frame)


class DisplayFilter(Filter):
    def __init__(self, win_name):
        self.win_name = win_name
        super().__init__()

    def process(self, frame):
        cv2.imshow(self.win_name, frame)
        cv2.waitKey(1)
        if not cv2.getWindowProperty(self.win_name, cv2.WND_PROP_VISIBLE):
            return False
        # probably can send some metadata/window size to then pass it to VideoSource
        return super().process(1)


class VideoSource(Filter):
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        super().__init__()

    def process(self, enabled):
        if not enabled:
            self.cap.release()
            return False
        ret, frame = self.cap.read()
        if not ret:
            self.cap.release()
            return False
        return super().process(frame)


def main():
    pipeline = Pipeline({
        'video': (VideoSource(VIDEO_PATH), ['mirror']),
        'mirror': (MirrorEffectFilter(), ['shaking']),
        'heart_effect': (HeartEffectFilter(), ['pink']),
        'pink': (PinkFilter(), []),
        'shaking': (ShakingFilter(), ['display']),
        'display': (DisplayFilter(WINDOW_NAME), ['video']),
    })
    pipeline.start()

    enabled_sink = pipeline.getSink('video')
    enabled_sink.put(True)

    while pipeline.isRunning('display') and pipeline.isRunning('video'):
        sleep(0.1)

    pipeline.stop()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
