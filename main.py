#/usr/bin/env python2.5
#-----------------------

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from google.appengine.ext.webapp import template

from suas import session, auth_handlers

HOME_VIEW = template.Template("""
<head><title>Home</title></head>
<body>
<h3>Demo app for <a href="http://github.com/aht/suas/">suas</a></h3>
{% if session.flash_msg %}
	<p>{{ session.flash_msg }}</p>
{% endif %}
{% if current_user %}
	<p>Logged in as {{ session.user.nick_name }}.</p>
	<p><a href="/logout">Log out</a></p>
{% else %}
	<p><a href="/login">Log in</a></p>
	<p><a href="/signup">Sign up</a></p>
{% endif %}
</body>
""")

class HomeHandler(session.RequestHandler):
	def get(self):
		ctx = template.Context({"session": self.session})
		self.response.out.write(HOME_VIEW.render(ctx))


ROUTES = [('/', HomeHandler)] + auth_handlers.ROUTES

APP = webapp.WSGIApplication(ROUTES, debug=True)

def main():
	util.run_wsgi_app(APP)

if __name__ == "__main__":
    main()
