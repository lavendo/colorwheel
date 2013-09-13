#!/usr/bin/env python

import argparse
import math
import os
import random
import re
import sys
import subprocess

class Color:
   def __init__(self, hue=0.0, saturation=0.0, luminosity=0.0):
      self.hue = hue # in degrees
      self.saturation = saturation
      self.luminosity = luminosity

   def chroma(self):
      return (1 - abs(2 * self.luminosity - 1)) * self.saturation

   def rgb(self):
      if self.hue < 0:
         self.hue += 360.0

      self.hue %= 360.0

      if self.luminosity < 0:
         self.luminosity = 0
      elif self.luminosity > 1.0:
         self.luminosity = 1.0

      if self.saturation < 0:
         self.saturation = 0
      elif self.saturation > 1.0:
         self.saturation = 1.0

      chroma = self.chroma()
      region = self.region()

      sub = chroma * (1 - abs(region % 2 - 1))
      dom = chroma
      triplet = [
         [dom, sub, 0.0],
         [sub, dom, 0.0],
         [0.0, dom, sub],
         [0.0, sub, dom],
         [sub, 0.0, dom],
         [dom, 0.0, sub]
      ][region]

      return map(lambda x: x + (self.luminosity - chroma * 0.5), triplet)

   def copy(self):
      return Color(self.hue, self.saturation, self.luminosity)

   def clone(self, color):
      self.hue = color.hue
      self.luminosity = color.luminosity
      self.saturation = color.saturation

   def blend(self, color, amount):
      hue_delta = (color.hue - self.hue) * amount
      lum_delta = (color.luminosity - self.luminosity) * amount
      sat_delta = (color.saturation - self.saturation) * amount

      return self + Color(hue_delta, lum_delta, sat_delta)

   def region(self):
      return int(round(self.hue / 60.0) % 6)

   def bright(self):
      return int(self.luminosity >= 0.5)

   def colorful(self):
      return int(self.saturation >= 0.5)

   def hex(self):
      return '#%02X%02X%02X' % tuple(map(lambda x: int(x*255) % 256, self.rgb()))

   def shifted_hue(self, hue):
      return Color(self.hue+hue, self.saturation, self.luminosity)

   def shifted_saturation(self, saturation):
      return Color(self.hue, self.saturation+saturation, self.luminosity)

   def shifted_luminosity(self, luminosity):
      return Color(self.hue, self.saturation, self.luminosity+luminosity)

   def __str__(self):
      return self.hex()

   def __repr__(self):
      return '<Color: %s>' % str(self)

   def __add__(self, color):
      new_color = self.copy()

      new_color.hue += color.hue
      new_color.saturation += color.saturation
      new_color.luminosity += color.luminosity

      return new_color

   def __sub__(self, color):
      new_color = self.copy()

      new_color.hue -= color.hue
      new_color.saturation -= color.saturation
      new_color.luminosity -= color.luminosity

      return new_color

   def __mul__(self, color):
      new_color = self.copy()
      
      new_color.hue *= color.hue
      new_color.saturation *= color.saturation
      new_color.luminosity *= color.luminosity

      return new_color

   def __div__(self, color):
      new_color = self.copy()
      
      if color.hue:
         new_color.hue /= color.hue
      else:
         new_color.hue = 0

      if color.saturation:
         new_color.saturation /= color.saturation
      else:
         new_color.saturation = 0

      if color.luminosity:
         new_color.luminosity /= color.luminosity
      else:
         new_color.luminosity = 0

      return new_color

   @classmethod
   def from_rgb(cls, r, g, b):
      r,g,b = map(lambda x: min(1.0,max(0.0,x if x<1.0 else min(255,x)/255.0)),(r,g,b))

      hue = math.degrees(math.atan2(math.sqrt(3) * (g - b), 2 * r - g - b))

      min_color = min(r,g,b)
      max_color = max(r,g,b)
      chroma = max_color - min_color

      luminosity = min(1.0, (min_color+max_color)/2.0)

      try:
         saturation = chroma / (1 - abs(2 * luminosity - 1))
      except ZeroDivisionError:
         saturation = 0.0

      return cls(hue, saturation, luminosity)

   @classmethod
   def from_rgb_string(cls, rgb):
      if rgb.startswith('#'):
         rgb = rgb[1:]

      if not len(rgb) == 6:
         raise Exception('damnit bobby now what did I tell you about color-hex')

      # hi, I'm a bitch
      return cls.from_rgb(*[int(rgb[h*2:h*2+2],16) for h in xrange(3)])

class Colorwheel:
   PITCH = 60.0
   OPPOSE = 180.0
   SHIFT = 0.0

   def __init__(self, **kwargs):
      self.primary_color = kwargs['primary_color']

      self.pitch = kwargs.setdefault('pitch', self.PITCH)
      self.oppose = kwargs.setdefault('oppose', self.OPPOSE)
      self.shift = kwargs.setdefault('shift', self.SHIFT)

   def primary(self):
      return self.primary_color.copy()

   def compliment(self):
      return self.primary_color.shifted_hue(self.oppose+self.shift)

   def positive_accent(self):
      return self.primary_color.shifted_hue(self.shift+self.pitch)

   def negative_accent(self):
      return self.primary_color.shifted_hue(self.shift-self.pitch)

   def compliment_positive_accent(self):
      return self.compliment().shifted_hue(self.shift+self.pitch)

   def compliment_negative_accent(self):
      return self.compliment().shifted_hue(self.shift-self.pitch)

   def compliment_hue(self, color):
      color.copy()
      color.hue = self.compliment().hue
      return color

   def compliment_positive_accent_hue(self, color):
      color.copy()
      color.hue = self.compliment_positive_accent().hue
      return color

   def compliment_negative_accent_hue(self, color):
      color.copy()
      color.hue = self.compliment_negative_accent().hue
      return color

class Palette(Colorwheel):
   PALETTE_MAP = dict()

   def __init__(self, **kwargs):
      palette_map = kwargs.setdefault('palette_map', self.PALETTE_MAP)
      self.palette_map = getattr(self, 'palette_map', dict())

      for color in palette_map.keys():
         self.palette_map[color] = palette_map[color]

      self.contrast = min(2.0,max(0.0,kwargs.setdefault('contrast', 1.0)))
      self.brightness = min(2.0,max(0.0,kwargs.setdefault('brightness', 1.0)))

      Colorwheel.__init__(self, **kwargs)

   def extend(self, palette_map):
      for color in palette_map.keys():
         if self.palette_map.has_key(color):
            continue

         self.palette_map[color] = palette_map[color]

   def from_palette(self, cls, palette_entry):
      return cls.PALETTE_MAP[palette_entry](self)

   def colors(self):
      colors = dict()

      for color in self.palette_map.keys():
         colors[color] = getattr(self, color)

      return colors

   def __getattr__(self, attr):
      if self.__dict__.has_key(attr):
         return self.__dict__[attr]

      if attr == 'palette_map':
         self.palette_map = Palette.PALETTE_MAP
         return self.palette_map

      if not self.palette_map.has_key(attr):
         raise AttributeError('no such palette item named %s' % attr)

      color = self.palette_map[attr](self)
      color.saturation *= self.contrast
      color.luminosity *= self.brightness

      return color

   def __str__(self):
      return '\n'.join(map(lambda x: '%s:%s' % (x[0], str(x[1])), self.colors().items()))

class PaletteGenerator:
   PALETTES = dict()
   DEFAULT_PALETTE = None

   def __init__(self, **kwargs):
      self.palettes = kwargs.setdefault('palettes', self.PALETTES)
      self.default_palette = kwargs.setdefault('default_palette', self.DEFAULT_PALETTE)

   def generate(self, color, palette=None):
      if not palette:
         palette = self.default_palette

      palette = self.palettes[palette]

      return palette(primary_color=color
                    ,pitch=self.pitch()
                    ,oppose=self.oppose()
                    ,shift=self.shift()
                    ,brightness=self.brightness()
                    ,contrast=self.contrast())

   def pitch(self):
      return Colorwheel.PITCH

   def oppose(self):
      return Colorwheel.OPPOSE

   def shift(self):
      return Colorwheel.SHIFT

   def brightness(self):
      return Palette.BRIGHTNESS

   def contrast(self):
      return Palette.CONTRAST

class CommandlinePaletteGenerator(PaletteGenerator):
   def generate(self):
      parser = argparse.ArgumentParser(description="Generate a colorscheme.")
      parser.add_argument('-P'
                         ,'--pitch'
                         ,type=float
                         ,default=60.0)
      parser.add_argument('-o'
                         ,'--oppose'
                         ,type=float
                         ,default=180.0)
      parser.add_argument('-s'
                         ,'--shift'
                         ,type=float
                         ,default=0.0)
      parser.add_argument('-b'
                         ,'--brightness'
                         ,type=float
                         ,default=1.0)
      parser.add_argument('-C'
                         ,'--contrast'
                         ,type=float
                         ,default=1.0)
      parser.add_argument('-p'
                         ,'--palette'
                         ,type=str
                         ,default='complimented')
      parser.add_argument('-c'
                         ,'--color'
                         ,type=Color.from_rgb_string
                         ,default='ff00ff')
      self.args = parser.parse_args()

      return PaletteGenerator.generate(self, self.args.color, self.args.palette)

   def pitch(self):
      return self.args.pitch

   def oppose(self):
      return self.args.oppose

   def shift(self):
      return self.args.shift

   def brightness(self):
      return self.args.brightness

   def contrast(self):
      return self.args.contrast

def DM(dict1,dict2,priority=1):
   dict1_keys = set(dict1.keys())
   dict2_keys = set(dict2.keys())

   all_elements = dict(dict1.items()+dict2.items())
   priority_dict = (dict1,dict2)[abs(priority) % 2]
   new_dict = dict()

   for key in (dict1_keys ^ dict2_keys):
      new_dict[key] = all_elements[key]

   for key in (dict1_keys & dict2_keys):
      new_dict[key] = priority_dict[key]

   return new_dict
