#/usr/bin/env python2.5
#-------------------

"""
Session based solely on signed cookie (no Datastore/memcache)

A CookieSession persists between HTTP requests & responses by using
signed cookies referring to a particular session ID.  All session-related
cookies are signed using the SID and the site's secret key, ensuring that:
	* In a key=value cookie, the value is really intended for the
		particular key.
	* Cookies are really pertinent to a particular SID that signed it.
	* Cookies were really issued by the server for a particular session.

The RequestHandler class extends webapp.RequestHandler to provide
access to the current session as an instance variable.

Limitations:
	* currently unsigned cookies are simply ignored
"""

from time import time, gmtime
from calendar import timegm
from hashlib import md5

from google.appengine.ext import webapp

from signedcookie import SignedCookie, BadSignatureError, SIG_LEN
from users import User

SECRET_KEY = 'Open, sesame!'
# A secret key unique to your application.

SESSION_TTL = 604800    # 604800s = 7d
# the life time of a "persistent" session authenticator, in seconds.
# As long as the user comes back within that time frame, we will nenew
# his session for a full period.  In case he doesn't, he will have to
# login again.

SID_TTL = 900           # 900s = 15m
# the minimum interval between requests after which
# we expire the old and issue a new ID.


class NoSIDError(Exception):
	pass

class CookieSession:
	"""
	Provides dictionary-like storage/access to signed cookies.
	The keys 'SID', 'user', and 'atime' are internally used by the
	session object and the request handler, do not change them.
	
	Attributes:
		user			the current user
		
		flash_msg	a possible flash message set by the previous page,
						automatically popped from the 'flash_msg' cookie
						
		cookies		the underlying cookies
	
	Class method:
		load(request, response)	returns a session instance loaded from cookies
	
	Instance methods:
		start(user, persist=False)
		end()

	Do not set/del the same key multiple times, as each __setitem__
	call adds a 'Set-Cookie' header in the response.  This is due
	to webapp's inability to deals directly with cookies or delete
	multi-valued headers.  You can modify the cookies attribute
	directly which do not modify the response, then call set_cookie
	to add a header manually.

	Also, since cookie values are strings, you will need to do
	serialization/deserialization yourself, if necessary.
	"""
	def __init__(self, user, response):
		self.user = user
		self.response = response
		self.persist = False
		id = self.__gen_id()
		self.cookies = SignedCookie(SECRET_KEY + id)
		self.cookies['SID'] = id
		self.cookies['atime'] = repr( timegm(gmtime()) )
	
	def __gen_id(self):
		# This is predictable, but that's ok.
		# We just need it to be unique, *especially* for different users
		if self.user is None:
			name = 'Anonymous'
		else:
			name = self.user.nickname
		return md5( name + repr(time()) ).hexdigest()
	
	def __getitem__(self, key):
		return self.cookies[key].value
	
	def get(self, key, default=None):
		v = self.cookies.get(key)
		if v is not None:
			return v.value
		else:
			return default
	
	def pop(self, key, default=None):
		try:
			v = self[key]
		except KeyError:
			if default is None:
				raise
			else:
				return default
		else:
			self.expire_cookie(key)
			return v
	
	def __setitem__(self, key, value):
		self.cookies[key] = value
		if self.persist:
			self.cookies[key]['max-age'] = SESSION_TTL
		self.set_cookie( key )
	
	def set_cookie(self, key):
		self.response.headers.add_header(
			'Set-Cookie', self.cookies[key].output()[12:]
			)
	
	def __delitem__(self, key):
		self.expire_cookie(key)
	
	def expire_cookie(self, key):
		self.cookies[key]['max-age'] = 0
		self.set_cookie( key )
	
	@classmethod
	def load(klass, request, response):
		"""
		Load the session cookies from the request,
		returning a new instance with the response.
		"""
		try:
			id = request.cookies['SID'][1:-SIG_LEN-1]
		except KeyError:
			raise NoSIDError
		else:
			c = SignedCookie(SECRET_KEY + id)
			c.load(request.environ['HTTP_COOKIE'])
			try:
				user = User.get_by_key_name(c['user'].value)
			except KeyError:
				user = None
			session = klass(user, response)
			session.cookies = c
			return session

	def start(self, user, persist=False):
		"""
		Log the user in, where user is an object with a nickname
		attribute.
		
		If persist=False, the browser will by default log the
		user out when it closes; otherwise we will keep him logged
		in as long as he comes back within SESSION_TTL.
		"""
		self.user = user
		self.persist = persist
		if user is None:
			self.set_cookie( 'SID' )
			self.set_cookie( 'atime' )
			if self.cookies.has_key ( 'user' ):
				self.expire_cookie ( 'user' )
		else:
			self.cookies['user'] = user.nickname
			self.regen()
		## TODO: Cache-control
	
	def regen(self):
		"""Regenerate a new SID"""
		id = self.__gen_id()
		c = SignedCookie(SECRET_KEY + id)
		for key, morsel in self.cookies.items():
			c[key] = morsel.value
			c[key].update( morsel.items() )		## preserves Max-Age
		c['SID'] = id
		c['atime'] = repr( timegm(gmtime()) )
		self.cookies = c
		for k in self.cookies.keys():
			self.set_cookie( k )
	
	def end(self):
		"""Expire all cookies"""
		self.user = None
		for key in self.cookies.keys():
			self.expire_cookie( key )


class RequestHandler(webapp.RequestHandler):
	"""
	A session-capable request handler.
	
	Attribute:
		session
	"""
	def initialize(self, request, response):
		super(RequestHandler, self).initialize(request, response)
		try:
			self.session = CookieSession.load(request, response)
		except NoSIDError:
			self.session = CookieSession(None, self.response)
		except BadSignatureError:
			self.session = CookieSession(None, self.response)
		else:
			self.session.flash_msg = self.session.pop('flash_msg', '')
			now = timegm( gmtime() )
			try:
				atime = int( self.session['atime'] )
			except ValueError:
				self.session.end()
				return
			if now - atime > SESSION_TTL:
				self.session.end()
				return
			if now - atime > SID_TTL:
				self.session.regen()

