# Read the installation instructions carefully before using

# 2022 update: I no longer work on this tool. v3.4.6 was the final version I worked on. Repo will however not be archived in case people want to contribute to.

# If you are updating from an old version that supports saved session, clear the session data by deleting the "data/backup" folder. There's an entity model change in v3.0.1 that will crash the tool upon launch if you don't clear the cached session.

# [v2.4.0 thread](https://www.reddit.com/r/StarlightStage/comments/pi9twn/score_simulator_aka_chihiro_v230240_duetencore/)

GitHub: [https://github.com/deresute-tools/deresute-tools](https://github.com/deresute-tools/deresute-tools)

Download (Windows only): [https://github.com/deresute-tools/deresute-tools/releases/latest](https://github.com/deresute-tools/deresute-tools/releases/latest)

Installation instructions:

* If you are new to the app: Download either **chihiro-python.rar** or **chihiro-cython.rar** (not the source code zip or tar!), extract wherever you want and run **chihiro.exe**. The cython release is faster but not a lot of testing has been done on it. Python release is the good ol' normal release, but can run a bit slower.
* For non-Windows platforms, you can install the python requirements in requirements.txt and run chihiro.py directly. I will not do a non-Windows release. If you get a virus warning from an AV, clone the repo, install the requirements and run chihiro.py
* To update: extract and overwrite your current version. Or copy the "data" folder from the old version to the new version.
* Quick patch: Only works in the same minor version (*a.b.\**). So if you are using 1.3.1 and want to update to 1.3.5, you can download 1.3.5 patch (chihiro.exe) and overwrite only the exe. But if you are using 1.2.2 and you want to update to 1.3.5, you have to download the full rar/zip package from any 1.3.x version, and apply the 1.3.5 patch.

How to use: [https://docs.google.com/document/d/e/2PACX-1vTjhwFyOT-pawJiBWhRjg9Edvx0AVcx1Dy-qw5QpNKG3HJhn2LuEl42dAxUVPaimv4O7xfJ1WFXTyz2/pub](https://docs.google.com/document/d/e/2PACX-1vTjhwFyOT-pawJiBWhRjg9Edvx0AVcx1Dy-qw5QpNKG3HJhn2LuEl42dAxUVPaimv4O7xfJ1WFXTyz2/pub)

Notable changes:

* **v3.0.0: Complete architecture rewrite, encore and OL now actually work. Accuracy and performance should be higher as well.**
* 2 releases: one stable one in pure python, one faster (but not fully tested) in cython.
* Added/moved some options to an extra config tab. Configs in this tab are saved upon app close and will be restored in the next session.
* Explanations for new options:
   * Disable Alt/Mutual/Ref (AMR) smuggling: as of this post (2021/09/18), encore in grand mode when copying AMR uses cached bonuses from the unit AMR is from, not from the unit that has encore. Enabling this option will force encore copied AMR to use bonuses from the encore unit instead.
   * Disable Magic smuggling: similar to the option above, encore when copying Magic across units in grand uses skills from the Magic unit, not from the unit that has encore. Enabling this option will force encore copied Magic to use skills from the encore unit instead.
   * Encore Magic can reso multiple boosts: this was the bug that forced cygame to close down grand mode for fixing on 2021/09/15. Magic only applies the max boosts on other skills, even in case of resonance units. However, encore copied Magic is not affected by this mechanism, allowing multiple boosts to be summed up, resulting in values as high as +200% boost per encore. Enabling this option will allow encore to use this erroneous behavior, in case you are curious how much people were scoring during these 2 days.
   * Allow GREATs in simulations: this option widens the random hit error range to allow GREAT hits to happen under 0 concentration condition. Note that in case there is a concentration skill in the build, disabling this option might still result in GREAT hits. In that case, run a perfect simulation.

Bug reports can be posted here or directly on the github issue tracker. However, please check the [issue tracker](https://github.com/deresute-tools/deresute-tools/issues) before reporting because there are low priority bugs that I already know and will not fix unless there is a change in priority.

Changelog:

* **v3.0.0: Complete architecture rewrite into using state machine for the simulation engine**
* Simulation engine partly written in cython for higher performance
* Extra options are split into 2 tabs, options in tab 2 are backed up upon app close / profile save using Ctrl+S

Known issues:

* Overestimating Helen center (forgot to implement for this release, low priority, will do some time in the future)

\---------

Pls fix grand, cygame.
