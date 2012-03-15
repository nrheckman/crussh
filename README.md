crussh: a modern cssh replacement
=================================

Backstory
---------

For anyone who needs to administrate clusters of many machines,
[clusterssh](http://sourceforge.net/projects/clusterssh/) has long been a
fallback for when the rest of your automation tools aren't working.

However, cssh has a number of deficiencies in modern environments:

- Doesn't play nice with window placement of modern window managers.
- Doesn't play nice with modern toolkits' copy and paste behaviour.
- Gets a bit screwy when there's more terminals than can fit on-screen.
- Doesn't support nice antialiased fonts.

crussh aims to be a simple replacement for cssh that corrects these
problems. It does so with the following features:

- Uses a single window to hold multiple terminals.
- Intelligently tiles terminals to fit available window size.
- Scrolls available terminals when they don't all fit in-window.
- Never resizes a terminal smaller than 80x24 characters.
- Uses GTK and the VTE widget to provide modern, anti-aliased terminals.

Install
-------

The install process is very simple on most distros:

- Install python2, python-gtk2, and python-vte.
- Run ./crussh.py hostname [hostname ...]

Bugs & TODO
-----------

To see current issues, report problems, and see plans for features,
see the [crussh GitHub issues page](https://github.com/unit3/crussh/issues).

Copyright and License
---------------------

crussh is copyright 2012 by Graeme Humphries <graeme@sudo.ca>.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see the
[GNU licenses page](http://www.gnu.org/licenses/).
