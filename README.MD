# Subtitle Creator/Editor using PyQt5
This is a modified version of the player example that comes with PyQt5. The program has been modified to support
subtitle (.srt) file creation with a (hopefully) self-explanatory UI.

Numpad (with NumLock enabled) is rewired to provide easy controls: <br>
  5: Play/Pause <br>
  4: Pause and step backward (custom millisecond amount) <br>
  6: Pause and step forward (custom millisecond amount) <br>
  7: Pause and mark current position as start <br>
  9: Pause and mark current position as end <br>
  2: Add subtitle text at currently marked start and end positions to the queue <br>

You can also use keys A, S, D, F, E, O to control the interface.
The control surface is toggled by pressing Ctrl + Tab.
  D: Play/Pause <br>
  A: Pause and step backward (custom millisecond amount) <br>
  F: Pause and step forward (custom millisecond amount) <br>
  S: Pause and mark current position as start <br>
  E: Pause and mark current position as end <br>
  O: Add subtitle text at currently marked start and end positions to the queue <br>

### Note: Requires K-Light Codec Pack to be installed to play videos in the application. Currently tested in Windows only (with latest Anaconda3)
