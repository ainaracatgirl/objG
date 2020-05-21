import tkinter
import threading
import os

windows = []
sprites = []

class Window:
    def __init__(self, funcname, env, w, h, title):
        self.funcname = funcname
        self.env = env

        self.root = tkinter.Tk(title)
        self.root.wm_title(title)
        self.root.resizable(False, False)
        self.canvas = tkinter.Canvas(self.root, width=w, height=h)
        self.canvas.pack()
        self.bg_color = "black"
        self.keycallback = None
        self.clickcallback = None
        self.root.bind("<Key>", self.onkey)
        self.root.bind("<Button-1>", self.onclick)
        self.root.bind("<Button-2>", self.onclick)
        self.root.bind("<Button-3>", self.onclick)
    
    def onkey(self, evt):
        if self.keycallback == None:
            return
        RunFunction(self.keycallback, self.env, [('string', str(evt.char)), ('number', int(evt.keycode))])

    def onclick(self, evt):
        if self.clickcallback == None:
            return
        RunFunction(self.clickcallback, self.env, [('number', int(evt.num)), ('number', int(evt.x)), ('number', int(evt.y))])

    def start(self):
        self.root.after(1, self._run)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
    
    def _run(self):
        self.canvas.delete('all')

        self.canvas.create_rectangle(0, 0, 640, 640, outline=self.bg_color, fill=self.bg_color)

        RunFunction(self.funcname, self.env)

        self.root.after(1, self._run)

def g2d_create(env, callback, w, h, title):
    global windows, Window
    _id = len(windows)

    windows.append(Window(callback[1], env, int(w[1]), int(h[1]), str(title[1])))

    return ('number', _id)

def g2d_start(env, _id):
    global windows, Window
    win = windows[int(_id[1])]

    win.start()
    return (None,)

def g2d_background(env, _id, color):
    global windows, Window
    win = windows[int(_id[1])]

    win.bg_color = color[1]
    return (None,)

def g2d_rect(env, _id, x, y, w, h, color):
    global windows, Window
    win = windows[int(_id[1])]

    x = int(x[1])
    y = int(y[1])
    w = x + int(w[1])
    h = y + int(h[1])
    color = str(color[1])

    win.canvas.create_rectangle(x, y, w, h, outline=color, fill=color)
    return (None,)

def g2d_line(env, _id, x1, y1, x2, y2, color):
    global windows, Window
    win = windows[int(_id[1])]

    x1 = int(x1[1])
    y1 = int(y1[1])
    x2 = int(x2[1])
    y2 = int(y2[1])
    color = str(color[1])

    win.canvas.create_line(x1, y1, x2, y2, fill=color)
    return (None,)

def g2d_ellipse(env, _id, x, y, w, h, color):
    global windows, Window
    win = windows[int(_id[1])]

    x = int(x[1])
    y = int(y[1])
    w = x + int(w[1])
    h = y + int(h[1])
    color = str(color[1])

    win.canvas.create_oval(x, y, w, h, outline=color, fill=color)
    return (None,)

def g2d_loadspr(env, path):
    global sprites
    _id = len(sprites)

    path = str(path[1])

    sprites.append(tkinter.PhotoImage(file=path))

    return ('number', _id)

def g2d_sprite(env, _id, x, y, spr):
    global sprites, windows, Window

    win = windows[int(_id[1])]

    x = int(x[1])
    y = int(y[1])

    win.canvas.create_image(x, y, image=sprites[int(spr[1])])
    return (None,)

def g2d_title(env, _id, title):
    global windows, Window

    win = windows[int(_id[1])]

    win.root.wm_title(str(title[1]))
    return (None,)

def g2d_onkey(env, _id, callback):
    global windows, Window

    win = windows[int(_id[1])]

    win.keycallback = str(callback[1]) 
    return (None,)

def g2d_onclick(env, _id, callback):
    global windows, Window

    win = windows[int(_id[1])]

    win.clickcallback = str(callback[1]) 
    return (None,)

AddAddonFunction("g2d_create", g2d_create)
AddAddonFunction("g2d_start", g2d_start)
AddAddonFunction("g2d_background", g2d_background)
AddAddonFunction("g2d_rect", g2d_rect)
AddAddonFunction("g2d_line", g2d_line)
AddAddonFunction("g2d_ellipse", g2d_ellipse)
AddAddonFunction("g2d_loadspr", g2d_loadspr)
AddAddonFunction("g2d_sprite", g2d_sprite)
AddAddonFunction("g2d_title", g2d_title)
AddAddonFunction("g2d_onkey", g2d_onkey)
AddAddonFunction("g2d_onclick", g2d_onclick)