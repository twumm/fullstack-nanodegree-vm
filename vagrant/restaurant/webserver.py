from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi

# CRUD operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem

#  session creating to enable DB connection
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.create_all(engine)
DBSession = sessionmaker(bind=engine)
session = DBSession()

class WebServerHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        try:
            restaurants = session.query(Restaurant).all()
            # opening localhost:8080/restaurants lists all the restaurants in the db
            if self.path.endswith("/restaurants"):
                # query restaurant list
                # restaurants = session.query(Restaurant).all()
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += "<html><body>"
                output += "<a href='/restaurants/new'>Create New Restaurant</a>"
                # use a for loop to list all restaurants
                for restaurant in restaurants:
                    output += "<h3> %s </h3>" %restaurant.name
                    output += "<a href='/restaurants/%s/edit' >Edit</a> " %restaurant.id
                    output += "<a href='/restaurants/%s/delete' >Delete</a>" %restaurant.id
                    output += "<br><br>"
                output += "</body></html>"
                self.wfile.write(output)
                print output
                return

            if self.path.endswith("/restaurants/new"):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                # add field and button to create new restaurant
                output = ""
                output = "<html><body>"
                output = "<h1>Enter the name of the new restaurant:</h1>"
                output += "<form method='POST' enctype='multipart/form-data' "\
                          "action='restaurants/new'>"\
                          "<input type='text' name='newRestaurantName' placeholder='New Restaurant'>"\
                          " <input type='submit' value='Create'></form>"
                output += "</body></html>"
                self.wfile.write(output)
                print output
                return

            if self.path.endswith("/edit"):
                restaurantIDPath = self.path.split("/")[2]
                myRestaurantQuery = session.query(Restaurant).filter_by(id=restaurantIDPath).one()
                if myRestaurantQuery:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    # display edit restaurant page
                    output = "<html><body>"
                    output += "<h1> %s </h1>" %myRestaurantQuery.name
                    output += "<form method='POST' enctype='multipart/form-data' action = '/restaurant/%s/edit'>" % restaurantIDPath
                    output += "<input name='newRestaurantName' type='text' placeholder='%s'>" % myRestaurantQuery.name
                    output += "<input type='submit' value='Rename'></form>"
                    output += "</body></html>"
                    self.wfile.write(output)
                    print output
                    return

            if self.path.endswith("/delete"):
                restaurantIDPath = self.path.split("/")[2]
                myRestaurantQuery = session.query(Restaurant).filter_by(id=restaurantIDPath).one()
                if myRestaurantQuery != []:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    # display delete page prompt
                    output = "<html><body>"
                    output += "<h1>Are you sure you want to delete %s?</h1>" %myRestaurantQuery.name
                    output += "<form method='POST' enctype='multipart/form-data' action='/restaurants/%s/delete'>" % restaurantIDPath
                    output += "<input type='submit' value='Delete'></form>"
                    output += "</body></html>"
                    self.wfile.write(output)
                    return

            '''if self.path.endswith("/hello"):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += "<html><body>Hello!"
                output += " <a href = '/hola' >Back to Hola</a> !"
                output += "<form method='POST' enctype='multipart/form-data' action="\
                          "'/hello'><h2>What would you like me to say?</h2><input name="\
                          "'message' type='text' ><input type='submit' value='Submit'>"\
                          " </form>"
                output += "</body></html>"
                self.wfile.write(output)
                print output
                return

            if self.path.endswith("/hola"):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += "<html><body"
                output += ">&#161Hola <a href = '/hello' >Back to Hello</a> "
                output += "<form method='POST' enctype='multipart/form-data' action="\
                          "'/hello'><h2>What would you like me to say?</h2><input name="\
                          "'message' type='text' ><input type='submit' value='Submit'>"\
                          " </form>"
                output += "</body></html>"
                self.wfile.write(output)
                print output
                return'''

        except IOError:
            self.send_error(404, 'File Not Found: %s' % self.path)

    def do_POST(self):
        try:
            if self.path.endswith("/restaurants/new"):
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                if ctype == 'multipart/form-data':
                    fields = cgi.parse_multipart(self.rfile, pdict)
                    messagecontent = fields.get('newRestaurantName')

                    # Create new Restaurant class and add user-gen restaurant
                    newRestaurant = Restaurant(name=messagecontent[0])
                    session.add(newRestaurant)
                    session.commit()

                    # Redirect to original restaurant homepage
                    self.send_response(301)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Location', '/restaurants')
                    self.end_headers()

            if self.path.endswith("/edit"):
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                if ctype == 'multipart/form-data':
                    fields = cgi.parse_multipart(self.rfile, pdict)
                    messagecontent = fields.get('newRestaurantName')
                    restaurantIDPath = self.path.split("/")[2]

                    myRestaurantQuery = session.query(Restaurant).filter_by(
                        id=restaurantIDPath).one()
                    if myRestaurantQuery != []:
                        myRestaurantQuery.name = messagecontent[0]
                        session.add(myRestaurantQuery)
                        session.commit()
                        # Re-direct to main page
                        self.send_response(301)
                        self.send_header('Content-type', 'text/html')
                        self.send_header('Location', '/restaurants')
                        self.end_headers()

            if self.path.endswith("/delete"):
                restaurantIDPath = self.path.split("/")[2]
                myRestaurantQuery = session.query(Restaurant).filter_by(
                    id=restaurantIDPath).one()
                print myRestaurantQuery
                if myRestaurantQuery:
                    session.delete(myRestaurantQuery)
                    session.commit()
                    # Re-direct to main page
                self.send_response(301)
                self.send_header('Content-type', 'text/html')
                self.send_header('Location', '/restaurants')
                self.end_headers()

            '''self.send_response(301)
            self.end_headers()

            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            if ctype == 'multipart/form-data':
                fields = cgi.parse_multipart(self.rfile, pdict)
                messagecontent = fields.get('message')

            output = ""
            output += "<html><body>"
            output += " <h2> Okay, how about this: </h2>"
            output += "<h1> %s </h1>" % messagecontent[0]

            output += "<form method='POST' enctype='multipart/form-data' action="\
                      "'/hello'><h2>What would you like me to say?</h2><input name="\
                      "'message' type='text' ><input type='submit' value='Submit'>"\
                      " </form>"
            output += "</body></html>"
            self.wfile.write(output)
            print output'''

        except:
            pass


def main():
    try:
        port = 8080
        server = HTTPServer(('', port), WebServerHandler)
        print "Web Server running on port %s" % port
        server.serve_forever()
    except KeyboardInterrupt:
        print " ^C entered, stoppinng web server...."
        server.socket.close()

if __name__ == '__main__':
    main()


