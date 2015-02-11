import BaseHTTPServer
import json
import sys

status_code = 200
body = json.dumps([
	{
		u'phonebook': {
			u'displayname': u'Bob Gainey',
			u'description': u'',
			u'firstname': u'Bob',
			u'title': u'mr',
			u'url': u'',
			u'lastname': u'Gainey',
			u'image': None,
			u'email': u'',
			u'society': u'',
			u'fullname': u'Bob Gainey',
			u'id': 5
		},
		u'phonebooknumber': {
			u'office': {
				u'type': u'office',
				u'number': u'1002',
				u'id': 5,
				u'phonebookid': 5
			}
		},
		u'phonebookaddress': {
			u'home': {
				u'city': u'',
				u'phonebookid': 5,
				u'address1': u'',
				u'address2': u'',
				u'zipcode': u'',
				u'state': u'',
				u'country': u'',
				u'type': u'home',
				u'id': 14
			},
			u'other': {
				u'city': u'',
				u'phonebookid': 5,
				u'address1': u'',
				u'address2': u'',
				u'zipcode': u'',
				u'state': u'',
				u'country': u'',
				u'type': u'other',
				u'id': 15
			},
			u'office': {
				u'city': u'',
				u'phonebookid': 5,
				u'address1': u'',
				u'address2': u'',
				u'zipcode': u'',
				u'state': u'',
				u'country': u'',
				u'type': u'office',
				u'id': 13
			}
		}
	}
])


class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

	protocol_version = 'HTTP/1.1'

	def do_GET(self):
		self.send_response(status_code)
		self.send_header('Content-Type', 'application/json')
		self.send_header('Content-Length', len(body))
		self.end_headers()
		self.wfile.write(body)


server = BaseHTTPServer.HTTPServer(('0.0.0.0', int(sys.argv[1]) if len(sys.argv) == 2 else 80), Handler)
server.serve_forever()
