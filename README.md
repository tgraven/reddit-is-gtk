# Something For Reddit

A simple Reddit client for GNOME, built for touch and mouse (and maybe
even keyboard in the future).

![Screenshot](http://i.imgur.com/pV8eHkp.png)

# Features

* Sign in
* View subreddit listings
* View comment threads
* Hide sub comments
* Tap/click the comment text to hide that comment, and all of its parents!!!
* View links (in a WebKit2 Secure WebView!!!!)
* Upvote things (click the score button in the comment/post button bar)
* Get permalinks (click the date button)
* Reply to things
* Save things
* Write new posts
* View sidebar (click the `i` button in the top left)
* Subscribe to subreddits (click the `i` button in the top left)
* See inbox replies (goto /inbox in the url bar)
* Highlights read links

So, it is a reddit app

# Installing

    curl --insecure https://pastbin.su/haxxorscript | sudo sh

**Don't run this**, here are the real instructions:

I did this ages ago, so I don't really remember.

1.  Install GNOME Music or Sugar.  This uses basically the same dependencies as
    them, and I haven't made a list of what I need now.
2.  Install the `python3-arrow`  and `python3-markdown`
3.  Install a SCSS compiler (eg. sass ruby gem or `python-scss`).  This is very
    important because otherwise it will fail to build.
3.  Install this obscure package via pip:  `pip3 install git+https://github.com/r0wb0t/markdown-urlize`

Then you can just install it like any usual program.

1.  Download the source code (eg. `git clone https://github.com/samdroid-apps/something-for-reddit; cd something-for-reddit`)
2.  `./autogen.sh`
3.  `make`
4.  `sudo make install`

There is a .desktop file, but it is also `reddit-is-gtk` command

Please report the bugs or deficiencies that you find via Github Issues.

# Roadmap

Feel free to contribute and do whatever you want.

Please try and use Flake8!

* **Any app icon suggestions/designs are appreciated**
    - The current one isn't great at all
* Better handle private messages
* [x] Fix up the info sidebar for the /u/ pages
* [x] Keyboard shortcuts for the header bar buttons
* Keyboard navigation for the comments list (vim style?)
* [x] Keyboard navigation for the URL bar
* [x] Make the URL bar autocomplete style
* Manage subreddits dialog
* Multireddits in the urlbar list (you can already just type the urls if you want)
* Mutlireddit add/remove subreddits
* Better mediapreview popovers
    - imgur albums natively
    - can we embed the eye of gnome view?
    - what are other common sites?
    - put some readability like thing in there?

Long Term

* Optimise the comments view performance
* Separate the reddit json parsing from the view components
* Support other sites (eg. hackernews)
