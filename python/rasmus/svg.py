import os


def color2string(color):
  return "rgb(%d,%d,%d)" % (int(255 * color[0]),
                            int(255 * color[1]),
                            int(255 * color[2]))

def colorFields(strokeColor, fillColor):
    return "stroke='%s' fill='%s' stroke-opacity='%f' fill-opacity='%f' " % \
        (color2string(strokeColor), 
         color2string(fillColor), 
         strokeColor[3],
         fillColor[3])

# common colors
#          r   g   b   a
red    = ( 1,  0,  0,  1)
orange = ( 1, .5,  0,  1)
yellow = ( 1,  1,  0,  1)
green  = ( 0,  1,  0,  1)
blue   = ( 0,  0,  1,  1)
purple = ( 1,  0,  1,  1)
black  = ( 0,  0,  0,  1)
grey   = (.5, .5, .5,  1)
white  = ( 1,  1,  1,  1)
null   = ( 0,  0,  0,  0)


class Svg:
    def __init__(self, stream):
        self.out = stream
    
    def close(self):
        self.out.close()
    
    
    def beginSvg(self, width, height):
        self.out.write(
            """<?xml version='1.0' encoding='UTF-8'?> 
            <!DOCTYPE svg PUBLIC '-//W3C//DTD SVG 1.1//EN' 
            'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd'>\n""")
        self.out.write(
            """<svg width='%d' height='%d' 
            xmlns='http://www.w3.org/2000/svg' version='1.1'>\n""" % \
            (width, height))
    
    def endSvg(self):
        self.out.write("</svg>")
    
    
    
    def line(self, x1, y1, x2, y2, color=black):
        self.out.write(
            """<line x1='%f' y1='%f' x2='%f' y2='%f' 
            stroke-opacity='%f' 
            stroke='%s' />\n""" % 
            (x1, y1, x2, y2, color[3], color2string(color)))
    
    
    def polygon(self, verts, strokeColor=black, fillColor=blue):
        self.out.write(
            "<polygon %s points='" % colorFields(strokeColor, fillColor))
        
        for i in xrange(0, len(verts), 2):    
            self.out.write("%f,%f " % (verts[i], verts[i+1]))
        self.out.write("' />\n")
    
    
    def rect(self, x, y, width, height, strokeColor=black, fillColor=blue):
        self.out.write(
            """<rect x='%f' y='%f' width='%f' height='%f' %s />\n""" % \
            (x, y, width, height, colorFields(strokeColor, fillColor)))
    
    
    def circle(self, x, y, radius, strokeColor=black, fillColor=blue):
        self.out.write("<circle cx='%f' cy='%f' r='%f' %s />\n" % \
            (x, y, radius, colorFields(strokeColor, fillColor)))
    
    def ellispe(self, x, y, xradius, yradius, strokeColor=black, fillColor=blue):
        self.out.write("<ellipse  cx='%f' cy='%f' rx='%f' ry='%f' %s />\n" %\
            (x, y, xradius, yradius, colorFields(strokeColor, fillColor)))
    
    
    def text(self, msg, x, y, size, strokeColor=null, fillColor=black,
             anchor="start", angle=0):
        
        anglestr = "transform='translate(%f,%f) rotate(%f)'" % \
                    (x, y, angle)
        
        self.out.write(
            "<g %s><text x='0' y='0' font-size='%f' %s text-anchor='%s'>%s</text></g>\n" % \
            (anglestr, size, colorFields(strokeColor, fillColor), anchor, msg))
    
    
    def text2(self, msg, x, y, size, strokeColor=null, fillColor=black,
             anchor="start", angle=0):
        
        if angle != 0:
            anglestr = "" #transform='rotate(%f,0,0)'" % angle
        else:
            anglestr = ""
        
        
        self.out.write(
            "<text x='%f' y='%f' font-size='%f' %s text-anchor='%s' %s>%s</text>\n" % \
            (x, y, size, colorFields(strokeColor, fillColor), anchor, 
            anglestr, msg))

    
    def beginTransform(self, *options):  
        self.out.write("<g transform='")
        
        for option in options:                
            key = option[0]
            value = option[1:]
            
            if key == "scale":
                self.out.write("scale(%f, %f) " % value)
            
            elif key == "translate":
                self.out.write("translate(%f, %f) " % value)

            elif key == "rotate":
                self.out.write("rotate(%f, %f, %f) " % value)

                    
            else:
                raise Exception("unknown transform option '%s'" % key)
        
        self.out.write("' >\n")
    
    def endTransform(self):
        self.out.write("</g>\n")
    
    
    def beginStyle(self, style):
        self.out.write("<g style='%s'>\n" % style)
    
    def endStyle(self):
        self.out.write("</g>\n")
    

    def write(self, text):
        self.out.write(text)


    def comment(self, msg):
        self.out.write("\n<!-- %s -->\n\n" % msg)





def convert(filename, outfilename = None):
    if outfilename == None:
        outfilename = filename.replace(".svg", ".gif")
    os.system("convert " +filename+ " " +outfilename)
    #os.system("rm " + filename)
    
    return outfilename



# testing
if __name__ == "__main__":
    svg = Svg(file("out.svg", "w"))
    
    svg.beginSvg(300, 500)
    
    svg.comment("MY COMMENT")
    
    svg.beginTransform(('scale', .5, .5))
    
    svg.line(0, 0, 100, 100, red)
    svg.rect(10, 10, 80, 100, black, (0, 1, 1, .5))
    svg.polygon([80,90, 100,100, 60,100], (0, 0, 0, 1), (0, 0, 1, .3))
    
    svg.endTransform()
    
    
    svg.beginStyle("stroke-width:3")
    svg.beginTransform(('translate', 200, 0))
    
    svg.line(0, 0, 100, 100, red)
    svg.rect(10, 10, 80, 100, black, (0, 1, 1, .5))
    svg.polygon([80,90, 100,100, 60,100], (0, 0, 0, 1), (0, 0, 1, .3))
    
    svg.endTransform()    
    svg.endStyle()
    
    svg.ellispe(150, 250, 70, 50, black, (.5, .5, .9, 1))
    svg.circle(150, 250, 50, black, red)
    svg.circle(150, 250, 30, white, blue)
    
    
    svg.text("Hello", 0, 400, 50, blue, (1, 0, 0, .1))
    
    
    for i in range(0, 300, 10):
        color = (i / 300.0, 0, 1 - i/300.0, 1)
        svg.rect(i, 450, 10, 50, color, color)
    
    svg.endSvg()
    svg.close()
    
    convert("out.svg")
