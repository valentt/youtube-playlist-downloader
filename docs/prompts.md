# User Prompts - YouTube Playlist Downloader

This document contains all user prompts/requests during the development of this project.

---

## Initial Request

**Prompt 1:**
> I would like to build youtube playlist downloader that works on both windows and linux, both for public playlists but also for private (once I'm logged into my account).

---

## Feature Specifications

**Prompt 2:**
> I would like it to have both gui and cli, if would download playlists in json format with optiona download of actual media files organizes in folders, with also option to monitor over time which links in playlist have become private or just dissapeared so json file should have some versioning and option so objects are tagges as "deleted" or "made private" or somehting like that, and cli and gui should have filter to show ones that have been made private or deleted (channel, author, title, and other yt metadata), video quality 1080p, audio only also as an option, no subtitles needed, resube if interrupted, 5 in parallel by default, downloads are organizes in same named folders. ask me additional questions.

**Prompt 3:**
> 1. both cookie and oauth as option. 2. json versioning both. 3. yes, if it appears agan mark it as "live" again, but that is very rare, but good catch. 4. we will run it manually for now. 5. pyqt/PySide. 6. track all metadata, small footprint so no reasin not to keep all. 7. PlaylistName/001 - VideoTitle.mp4 (with playlist position numbers).

---

## Environment Setup

**Prompt 4:**
> lets create python environment so it is separate from system pip so libraries have separate space, update docs and anything else needed

---

## Git & GitHub

**Prompt 5:**
> push this to github as V1.0.0, make cookies.txt .venv/ and downloads/ and .claude/ as gitignore

**Prompt 6:**
> is it done?

**Prompt 7:**
> what do I need to do?

**Prompt 8:**
> I'll give you github right, what commands do you need to be installed? I saw gh failing

**Prompt 9:**
> C:\Windows\system32>winget install --id GitHub.cli / 'winget' is not recognized...

**Prompt 10:**
> gh is now installed

**Prompt 11:**
> https://github.com/valentt/youtube-playlist-downloader

---

## Enhancement: Channel Display

**Prompt 12:**
> We need to make some enhancements. we don't heed playlist ID in "Playlists" tab, but instead playlist ID show Channel name or user name.

---

## Performance & Progress

**Prompt 13:**
> I added playlist with 220 items and it took 10 minutes do populate playlist, why is it taking so long? Is there any way we can speed this up. Also it is annoying that in GUI there is no progress while this is happening, but you can see progress in command line. we need progress bar and time estimate

**Prompt 14:**
> this new download is very fast but it doesn't show which are removed and reason for removal:
> ```
> WARNING: [youtube:tab] YouTube said: INFO - 1 unavailable video is hidden
> ```

**Prompt 15:**
> what was previous playlist download doing? I liked that it showed reason why some file is missing.

**Prompt 16:**
> ERROR: [youtube] Bd-1TX54Flg: This video has been removed for violating YouTube's policy on nudity or sexual content

**Prompt 17:**
> is it possible to find info about deleted videos - which channel was it on or any other info?

**Prompt 18:**
> ok, give option to do "fast" playlist download or detailed metadata (slow). I want both options. Also if list was grabbed by fast we shhould have option to download detailed metadata for whole playlist or if I click on individual one just for that one. I like Option 2: Better Initial Metadata, do that

---

## Unavailable Videos & Rate Limiting

**Prompt 19:**
> have button to show/hide removed videos from playlist. there are quite a few unavailable on my favorites playlist but when I choose status anything but live or all I get empty list. But you can see that these videos are unavailable, so please keep them also in json database
>
> [Shows console output with rate-limiting errors like:]
> ```
> [youtube] 5klX2_wj6jE: Downloading web safari player API JSON
> ERROR: [youtube] 5klX2_wj6jE: Video unavailable. This content isn't available, try again later. The current session has been rate-limited by YouTube for up to an hour.
> ```

---

## Download Status & Single Item Download

**Prompt 20:**
> I downloaded all 28 items from my music playlist in audio format but in gui it is showing them as downloaded video, there should be separate status for downloaded video and downloaded audio files. ALso one item wasn't downloaded and there should be way to click on single item and just download that item as video or audio.

---

## Documentation

**Prompt 21:**
> save all of my prompts into prompts.md

---

## Comments Download Feature

**Prompt 22:**
> is it possible to add feature to download all comments into md format?

---

## UX Improvement - Separate Download Options

**Prompt 23:**
> aaaah, that is bad UX, remove "Metadata only" add checkbox for video so that we have: video, audio, comments as download options.

---

## Enrichment & Progress Improvements

**Prompt 24:**
> video 4 is shown as unavailable, that is ok. but video id is missing. unavailable_4
>
> enriching is not showing in cli, put full log in cli when doing enriching, same as you are downloading full list. when doing enrichment in video tab progress is working and it is great, but when in playlists tab and clicking to fetch full metadata there is no progress in percentages, why?
>
> also playlist folders should have "Channel - Name" not "playlistID" as folder name, this is not human friendly

---

## Playlist Context Menu

**Prompt 25:**
> right click on playlist in playlist tab should give option to delete playlist or to open its url in external browser

---

## Fix Video ID Extraction for Unavailable Videos

**Prompt 26:**
> video4 is still showing unavailable_4 but in download logs you can see video id so save it from download log.
>
> [Shows logs where video ID `OERLEFnVOWc` is visible but was being saved as `unavailable_4`]

---

## Storage Folder Naming

**Prompt 27:**
> [Shows directory listing of `playlists/` folder still using playlist IDs like `PL0DH5xkJlZAb8wjrDGkOzv3UNA2ANdly1`]
>
> still using playlist id instead of what I said

**Prompt 28:**
> and rename current playlist folders so that they work as expected with new naming schema
>
> No, channel name is Valent Turkovic, not dr Wesin

**Prompt 29:**
> still showing only unanailable video but no video id after downloading full metadata playlist

**Prompt 30:**
> great now it works, update all files before we end for now

---

## Version 1.1.0 Release

**Prompt 31:**
> create new minor release v1.1.0

---

## External Repository Analysis

**Prompt 32:**
> analyze this repo - https://github.com/mattwright324/youtube-metadata is there anything that we can get by using this repo for metadata?

**Prompt 33:**
> save this as report in md file

---

## Documentation Updates

**Prompt 34:**
> update prompts and claude.md

---

## Archive.org Integration

**Prompt 35:**
> add option to upload selected files to archive.org, how would you do it? make a plan and ask me additional questions

**Prompt 36:**
> do research first and make a plan

**Prompt 37:**
> A

**Prompt 38:**
> update al and give me summary, write also prompts.md

---

## Rate Limiting & Anonymous Mode

**Prompt 39:**
> there should be way to unload cookies, my youtube account got blocked and it could be due to using this tool too much so I would like also to have anonymous mode where I download everything that is public on youtube without using cookies also

**Prompt 40:**
> I entered my s3 access and secret key in gui but got error that my account is not found, how can we test just webarchive module if it works as expected

**Prompt 41:**
> aha, so I need to download video first then archive it? Is there also way to archive it via youtube link only?

**Prompt 42:**
> archive is not allowing me to upload because video is still available on youtube, this is not how this tool should work, it should archive no matter what if I give it archive command

**Prompt 43:**
> add feature to open video, audio or comment file via context menu. it shoul just start defualt os viewer for those files

---

## Upload Progress Tracking

**Prompt 44:**
> I started archiving one file, is there way to get some progress info in gui and in cli? in cli there is nothing but I would like to see output there. just tell me if it is possible and how

**Prompt 45:**
> is there a way for you to measure how much data you are sending out and measure that as way to get some progress?

**Prompt 46:**
> make a detailed plan and save it as md file

**Prompt 47:**
> go for it
