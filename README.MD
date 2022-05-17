# Subtitle Creator/Editor using PyQt5
This is a modified version of the player example that comes with PyQt5. The program has been modified to support
subtitle (.srt) file creation with a (hopefully) self-explanatory UI.

Numpad (with NumLock enabled) is rewired to provide easy controls: <br>
  5: Play/Pause <br>
  4: pause and Step Backward (custom millisecond amount) <br>
  6: Pause and Step Forward (custom millisecond amount) <br>
  7: Mark current position as start <br>
  9: Mark current position as end <br>
  2: Add subtitle text at currently marked start and end positions to the queue <br>

### Note: Requires K-Light Codec Pack to be installed to play videos in the application. Currently tested in Windows only (with latest Anaconda3)
