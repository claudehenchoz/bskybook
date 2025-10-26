bskybook is a python command-line tool that will create an epub 2 ebook from a BlueSky feed.

it does this by getting a list of most recent posts (20 by default) in a specified account (use the anonymous bluesky api for that, preferably using requests), will then extract the links, will then use the trafilatura library to get and turn the content into markdown, will then turn the markdown into xhtml 4 (as per epub 2 spec) and generate a nicely formatted epub file.

it generates a cover by taking the thumbnail images from all the linked articles (use the image in <meta property="og:image"> from each page) then combining them into a mosaic to create a cover in the resolution of 1680x1264 (ereader resolution). use the pillow library to do that.

test it using this feed: https://bsky.app/profile/republik.ch
