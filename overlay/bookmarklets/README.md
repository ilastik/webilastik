You can use these bookmarkelts as a quick way to inject ilastik either onto neuroglancer (`inject_into_neuroglancer`) or into any other web page (`inject_into_img`). Just reate a new bookmark in your web browser bookmark toolbar and paste the contents of the bookmarklet file into the URL field of the bookmark.

You will need to compile the appropriate bundle for the injection to work: either `npm run bundle-ng-inject` or `npm run bundle-img-inject`.

The bookmarklets assumes that ilastik is in being hosted at `localhost`; Edit the host names as needed.
