# aib2ofx.user.js

For the moment it's only working under Firefox, as it uses `@require`
and few `GM_*` calls, that are not available under Chrome. And I'm too
lazy to rewrite it for Chrome, given that proper, browser-indepedent
version is coming. It should be sufficient for getting the data out, I
was using it for some time now with Wesabe.

* Install on Firefox with recent GreaseMonkey extension.
* Log in to your personal bank account in AIB.
* Click on `Statements`.
* Click on `QFX` link.

The resulting file has "ugly" name, but there's little I can do
without bringing Flash in, or bouncing the resulting data off a
server. Complain [here](https://bugzilla.mozilla.org/show_bug.cgi?id=532230)
if you also think that things should work better.