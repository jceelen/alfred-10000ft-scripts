# 10.000ft Scripts - Workflow for Alfred #
10.000ft workflow for Alfred, the aim is to make working with 10.000ft faster.

This script is a very simple first version and a research project and not really meant for distribution (yet) but just try it! And please, [give me feedback!](https://github.com/jceelen/alfred-10000ft-scripts/issues) :-). I am happy to help with questions.

## Features ##
- saves your API key in the OSX Keychain
- gets realtime data (and saves it in cache) from 10.000ft using the API
- opens the edit page of a project directly from Alfred

## Download and installation ##
Download the latest version from the [GitHub releases page](https://github.com/jceelen/alfred-10000ft-scripts/releases/latest)

Copy your API key to the clipboard, and use `.10ksetkey` to save your API key

[Request your 10.000ft API Key](http://10000ft.us6.list-manage2.com/subscribe?u=9c2ec42cba0e4196798807690&id=be8afd4d34)

## Usage ##
- `.10ksetkey` — saves your 10.000ft API key to the OSX Keychain
- `.10ksetuser` — sets your 10.000ft User-tag-name (for feature in the future)
- `.10kupdate` — forces update of your 10.000ft project data
- `10k projects` — shows a list of active projects which you can filter

### Shortcuts ###
- `10k home` — open your 10000ft.com homepage
- `10k schedule` — open the Schedule view
- `10k analytics` — open the Analytics view

## Changelog

#### v0.4
- Added submenu with options for every project
- Changed usage
- Add create report for project
- Add view project
- Fixed caching
- Simplified workflow in Alfred
- Added project icons based on status (confirmed, tentative, internal)

#### v0.3
- Added automatic updates


## Thanks ##
This workflow uses the awesome [Alfred-Workflow](http://www.deanishe.net/alfred-workflow/) library [MIT-licensed](http://opensource.org/licenses/MIT).