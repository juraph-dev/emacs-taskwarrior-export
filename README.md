# emacs-taskwarrior-export
Born from necessity. Org-mode is goated for managing information, but the visualisation for agendas/task tracking is dogshit. Taskwarrior has fantastic visualisation and tracking functionality, but is absolutely not designed for managing information. Why not both?

This script iterates through an org-mode file, looking for ```TODO``` tags to mark as taskwarrior tasks. It can also handle a few org-mode ```SCHEDULED``` tags, such as: 
``` org
SCHEDULED: <2024-06-10 Mon 14:00> \
SCHEDULED: <2024-06-10 Mon 14:00 +1w> \
SCHEDULED: <2024-06-10 Mon 14:00-15:00 +1w> \
SCHEDULED: <2024-04-02 Tue>--<2024-04-04 Thu> \
```
If a task has been marked ```DONE```, it will mark the existing taskwarrior task as completed.
and will assign deadlines, recurances etc. It will also scan for priorities (```[#A], [#B] [#C]```), and translated them to (```H,M,L```) taskwarrior priorities.

Very barebones for now, just experimenting with the concept to see if it fits into my workflow. I wasn't super happy with what was out there for exporting org mode files to taskwarrior tasks, so took a stab at it myself.
