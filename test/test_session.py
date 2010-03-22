#!/usr/bin/nosetests --with-gae

import re
from time import time, gmtime
from calendar import timegm
from webtest import TestApp

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

# hack the path
import sys, os
sys.path.append( os.path.abspath( os.path.join( os.path.dirname(__file__), '..') ) )

from signedcookie import SignedCookie, SIG_LEN
from session import RequestHandler, SECRET_KEY, SESSION_TTL, SID_TTL

# mock
class User:
	def __init__(self, nickname):
		self.nickname = nickname

class Login(RequestHandler):
	def post(self):
		nickname = self.request.get('nickname')
		self.session.start(User(nickname))

class Regen(RequestHandler):
	def post(self):
		self.session.regen()

class Touch(RequestHandler):
        def get(self):
                pass

class Logout(RequestHandler):
	def get(self):
		self.session.end()

def application():
	return webapp.WSGIApplication(
			[	('/login', Login),
				('/regen', Regen),
				('/touch', Touch),
				('/logout', Logout)	],
			debug=True)

def test_login():
	app = TestApp(application())

	## forge the session cookie ##
	app = TestApp(application())

	response = app.post( '/login', {'nickname': 'foo'} )

	res = str(response)
	assert 'SID=' in res
	assert 'user="foo' in res
	assert 'atime=' in res

def test_logout():
	app = TestApp(application())

	## forge the session cookie ##
	SID = 'safd32hfsdasdh'
	c = SignedCookie(SECRET_KEY + SID)
	c['SID'] = SID
	c['user'] = 'foo'
	c['atime'] = timegm( gmtime() )
	s = 'Cookie: '+ '; '.join( m.output()[12:] for m in c.values() )
	
	response = app.get('/logout', extra_environ={'HTTP_COOKIE': s})
	
	res = str(response)
	assert re.search('SID=.*Max-Age=0', res)
	assert re.search('user="foo.*Max-Age=0', res)
	assert re.search('atime=.*Max-Age=0', res)

def test_regen():
	app = TestApp(application())

	## forge the session cookie ##
	SID = 'sfh98324igfnad'
	c = SignedCookie(SECRET_KEY + SID)
	c['SID'] = SID
	c['user'] = 'foo'
	c['atime'] = timegm( gmtime() )
	s = 'Cookie: '+ '; '.join( m.output()[12:] for m in c.values() )
	
	response = app.post('/regen', extra_environ={'HTTP_COOKIE': s})
	
	res = str(response)
	new_SID = re.search('SID="(.*)"', res).group(1)
	new_user = re.search('user="(.*)"', res).group(1)
	assert new_SID[:-SIG_LEN] != c['SID'].value
	assert new_user[:-SIG_LEN] == c['user'].value
	assert new_user != c['user'].coded_value

def test_autoregen():
	app = TestApp(application())

	## forge the session cookie ##
	SID = 'klah23dsfohdshds82'
	c = SignedCookie(SECRET_KEY + SID)
	c['SID'] = SID
	c['user'] = 'foo'
	c['atime'] = timegm( gmtime() ) - SID_TTL - 1
	s = 'Cookie: '+ '; '.join( m.output()[12:] for m in c.values() )
	
	response = app.get('/touch', extra_environ={'HTTP_COOKIE': s})
	
	res = str(response)
	new_SID = re.search('SID="(.*)"', res).group(1)
	new_user = re.search('user="(.*)"', res).group(1)
	assert new_SID[:-SIG_LEN] != c['SID'].value
	assert new_user[:-SIG_LEN] == c['user'].value
	assert new_user != c['user'].coded_value

def test_autoexpire():
	app = TestApp(application())

	## forge the session cookie ##
	SID = 'afds87asg3hasdf'
	c = SignedCookie(SECRET_KEY + SID)
	c['SID'] = SID
	c['user'] = 'foo'
	c['atime'] = timegm( gmtime() ) - SESSION_TTL - 1
	s = 'Cookie: '+ '; '.join( m.output()[12:] for m in c.values() )
	
	response = app.get('/touch', extra_environ={'HTTP_COOKIE': s})
	
	res = str(response)
	assert re.search('SID=.*Max-Age=0', res)
	assert re.search('user=.*Max-Age=0', res)
	assert re.search('atime=.*Max-Age=0', res)

