# OpenFDD Controller

This is a sample frontend for [OpenFDD](https://github.com/zeGolem/openfdd). It's still
very, _very_ experimental, but it works enough to be usable for testing purposes.

Working using openfdd@ec29878c872bf17a8eeef55ed1d285df4d47c18d

# Running

You'll need Python 3 and PyQt5 installed on your system. Then, run with

```console
$ ./main.py
```

(NOTE: The openfdd daemon must be running for this to work)

# Known issues

- Not enough error handling. It can crash very easily, as well as silently fail even
  more easily. Don't rely on it for day-to-day use. Double check the commands it's sending
  in your terminal. All the time.
- No support for reading notifications. This causes issues if you (un)plug a USB device while
  the  program is running. Maybe plug notifications should be optional in openfdd?
- Everything else marked as `# TODO:` in the code.

This software is for demo purposes only.
