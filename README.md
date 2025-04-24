# Github star timeline cli
**@readwithai** - [X](https://x.com/readwithai) - [blog](https://readwithai.substack.com/) - [machine-aided reading](https://www.reddit.com/r/machineAidedReading/)

`gh-star-timeline` maintains a timeline of the number of stars that a [Github](https://github.com/github) repository has over time.

Basic statistical aggregates can be queried offline.

## Alternatives and prior work
There are many open source projects on github which do similar things.

[starcount](https://github.com/starkblaze01/Star-Count) and [gh-stars](https://github.com/jonschlinkert/gh-stars) fetch the number of stars for all repositories a user has, but at a specific point in time. I have reimplemented much of this functionality here because I wanted to maintain a timeline. One could alternatively wrap this tool.

[star history](https://www.star-history.com/) can produce plots (but only plots) of the historic number of starts for a repository and is [open source](https://github.com/star-history/star-history).  I believe this uses the `stargazers` api which can provide the time that a repository was starred (See  [this snippet](https://gist.github.com/jasonrudolph/5abee158b42b99a3990a))

This sort of timeline can be regenerated (up-to stars being removed) from ghis snippet.

I have a similar project, [gh-views](https://github.com/talwrii/gh-views), which fetches the number of views and clones for repository.

## Installation
You can install `gh-star-timeline` using [pipx](https://github.com/pypa/pipx):

```
pipx install gh-star-timeline
```

You must also install the github command-line tool [gh](https://github.com/cli/cli) and log in to github with `gh auth login`.

# Usage
To fetch the total number of stars for a repository you can run e.g.
```
gh-star-timeline talwrii/ffmpeg-cookbook
```

To see documentation for `gh-star-timeline` you can use:

```
gh-star-timeline --help
```

To get the number of stars for each repo (analogous to [starcount](https://github.com/starkblaze01/Star-Count). This can be a little slow. It should be faster on later runs.

```
gh-star-timeline --user talwrii
```

You can use the `-n` option to use fetched data.

If you want the total number of stars for all your repositories, you can run:
```
gh-star-timeline --user talwrii -n --total
```
You can use `-T` instead of `--total`


To get a timelime of all stars added (or removed while you where using `gh-star-timeline`), you can run:
```
gh-star-timeline talwrii/curlfire --stars -n
```

To get a timeline of stars counts over time you can use `--timeseries`
```
gh-star-timeline  talwrii/curlfire -n --timeseries
```
It would be relative easy to place this information on a graphical plot using any programming language or spreadsheet.

You can get a timeseries of the total number of stars across all your repos with:
```
gh-star-timeline  talwrii/curlfire -n --timeseries -T
```

### Periodically fetching
You can fetch a complete history of star counts (apart from removed stars) at any time by running *without* the `-n` option. You may like to run periodically to keep your local stats up-to-date and detect people removing stars.

This could be done with a [systemd timer](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) or [cron job](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/) or a variety of other methods.

### Backing up data
Data is stored in `~/.local/state/gh-star-timeline`. You may wish to periodically back up this data.

## Caveats
`gh-star-timeline` was written and tested on Linux. It will probably work on Mac without any alteration. The paths that `gh-star-timeline` uses to store data may need to be adapted for Windows. This should be an easy change if you are familiar with the Python programming language and I will accept and quickly merge any pull requests which add support for other systems.

## Reporting Issues
If you find any issues it would be helpful for me and other users if you report them to me via [Github issues](https://github.com/talwrii/gh-star-timeline/issues).

## Support
If you find this project useful,  you could pay me money ($3 maybe) through my [ko-fi](https://ko-fi.com/c/965d8a3fca). This will incentivize me to respond to issues with this repo and work on [similar command-line tools](https://readwithai.substack.com/p/my-productivity-tools)

You could also look at a similar tool I made to track views and clones of a github repo: [gh-views](https://github.com/talwrii/gh-views). Or read some of the things that I have written about note-taking and reading. Perhaps this [review of note-taking in Obsidian](https://readwithai.substack.com/p/note-taking-with-obsidian-much-of) would be a good starting point.

## About me
I am **@readwithai** I make tools for reading, research, and agency sometimes using [Obsidian](https://readwithai.substack.com/p/what-exactly-is-obsidian).

You can follow me on [X](https://x.com/readwithai) where I write about many things - including productivity tools like this. Or you can read my [blog](https://readwithai.substack.com/) where I write more around reading and research

![@readwithai logo](./logo.png)
