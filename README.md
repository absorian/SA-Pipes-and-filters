# SA A4: Pipes and filters
The project contains the implementation of mentioned pattern and an example use. Implementation is based on threading (`threading.Thread`) and queues (`queue.SimpleQueue`).
### The structure
- Base class: **Filter**. Manages internal input and output pipes and filter's process.
- Control class: **Pipeline**. Arranges filters and pipes between them, controls the state of filters, and provides endpoints to the user.
- Main derived classes, that accept an image frame and apply the actual filter outputting the processed frame:
  - **PinkFilter**
  - **ShakingFilter**
  - **HeartEffectFilter**
  - **MirrorEffectFilter**
- Filter endpoints, that accept *control data* and output a frame and vice versa:
  - **DisplayFilter**
  - **VideoSource**
- Main function where the initialization and control loop are placed.
