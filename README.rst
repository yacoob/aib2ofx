====
aib2wesabe
====
or how to suck data out of AIB's online interface, and format it into OFX file.

This gizmo should consist of following parts:
* aib.py - AIB handling (login/data scraping)
* cfg.py - configuration handling
* ofx.py - data formatter

There's also (already working!) rudimentary GreaseMonkey version. For the
moment it's only working under Firefox, as it uses @require and few GM_* calls,
that are not available under Chrome. And I'm too lazy to rewrite it for Chrome,
given that proper, browser-indepedent version is coming. It should be
sufficient for getting the data out, I was using it for some time now
with Wesabe.
