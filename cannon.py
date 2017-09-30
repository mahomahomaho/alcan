from math import radians

from cymunk import Vec2d, PivotJoint
from kivy.properties import NumericProperty, ObjectProperty

from anim import AnimObject
import defs
from utils import observe as O


class Cannon(AnimObject):
    collision_type = 2
    aim = NumericProperty(0)
    offset = ObjectProperty((0, 0))

    def __init__(self, *args, **kwargs):
        self.layers = defs.CARRIED_THINGS_LAYER
        super(Cannon, self).__init__(*args, **kwargs)

        self.bullets = []

    def create_shape(self):
        """ make cannon a sensor """
        shape = super(Cannon, self).create_shape()
        shape.sensor = True
        return shape

    def carry_element(self, element, __dt=None):
        # unbind joint from element
        element.unjoint()

        # move it to center of cannon
        pivot = self.body.position + Vec2d(self.offset)
        element.body.position = pivot
        element.joint = O(PivotJoint(self.body, element.body, pivot))
        self.space.add(element.joint)

        self.bullets.append(element)

    def shoot(self):
        impulse = Vec2d(0, defs.shoot_force)
        impulse.rotate(radians(self.aim))
        for x in self.bullets:
            x.unjoint()
            x.body.apply_impulse(impulse)
            x.shape.layers = defs.SHOOTED_THINGS_LAYER
            x.activate()
        self.bullets = []