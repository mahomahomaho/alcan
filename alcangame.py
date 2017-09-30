from functools import partial
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Keyboard, Window
from kivy.logger import Logger
from kivy.properties import NumericProperty
from kivy.uix.widget import Widget

from anim import AnimObject, PhysicsObject
from baloon import Baloon
from cannon import Cannon
import defs
from element import Element
from oninitmixin import OnInitMixin
from wizard import Wizard
from other import GameOver


class AlcanGame(Widget, PhysicsObject, OnInitMixin):

    bfs = NumericProperty('inf')

    def __init__(self, *args, **kwargs):

        Window.size = defs.map_size

        super(AlcanGame, self).__init__(*args, **kwargs)

        self.oo_to_remove = set()
        self.oo_to_add = []
        self.num_elements_in_zone = 0
        self.keys_pressed = set()

        from kivy.base import EventLoop
        EventLoop.window.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)

        self.update_event = Clock.schedule_interval(self.update, 1.0/defs.fps)

        # collision handlers
        self.space.add_collision_handler(Wizard.collision_type,
                                         Element.collision_type,
                                         self.wizard_vs_element)
        self.space.add_collision_handler(Element.collision_type,
                                         Cannon.collision_type,
                                         self.cannon_vs_element)
        self.space.add_collision_handler(Element.collision_type,
                                         Element.collision_type,
                                         self.element_vs_element)
        self.space.add_collision_handler(Element.collision_type,
                                         defs.BOTTOM_BOUND,
                                         self.element_vs_bottom)
        self.space.add_collision_handler(Wizard.collision_type,
                                         defs.BOTTOM_BOUND,
                                         self.wizard_vs_bottom)

        Window.bind(on_resize=self.on_resize)
        self.bfs = Element.steps_to_reach()

    def clear(self):
        self.update_event.cancel()
        self.update_event = None
        for x in self.children[:]:
            if isinstance(x, AnimObject):
                self.remove_widget(x)
        self.del_physics()


    def on_init(self):
        self.add_widget(Baloon(center=(300, 300), object_to_follow=self.wizard,
                               text="Alchemist"))
        Clock.schedule_once(lambda dt: self.add_widget(Baloon(center=(400, 300), size=(200, 50),
                                                       object_to_follow=self.cannon,
                                                       text="Large Elements Collider")),
                            3)

    def schedule_add_widget(self, oclass, *oargs, **okwargs):
        self.oo_to_add.append((oclass, oargs, okwargs))

    def remove_obj(self, obj, __dt=None, just_schedule=True):
        if just_schedule:
            Logger.debug("game: schedule %s to be removed", obj)
            self.oo_to_remove.add(obj)
            return
        Logger.info("game: remove object obj=%s", obj)
        obj.before_removing()
        self.space.remove(obj.body)
        self.space.remove(obj.shape)
        self.remove_widget(obj)
        del self.bodyobjects[obj.body]

    def replace_obj(self, a, BClass, *Bargs, **Bkwargs):
        self.remove_obj(a)
        Bkwargs['center'] = a.center
        Bkwargs['size'] = a.size
        self.schedule_add_widget(BClass, *Bargs, **Bkwargs)

    def wizard_vs_element(self, __space, arbiter):
        """ collision handler - wizard vs element """
        wizard, element = [self.bodyobjects[s.body] for s in arbiter.shapes]

        if isinstance(wizard, Element):
            wizard, element = element, wizard

        if wizard.carried_elements:
            return True

        Clock.schedule_once(partial(wizard.carry_element, element))

    def cannon_vs_element(self, __space, arbiter):
        cannon, element = [self.bodyobjects[s.body] for s in arbiter.shapes]

        if isinstance(cannon, Element):
            cannon, element = element, cannon

        if cannon.bullets:
            return True  # cannot hold more than one bullet

        return Clock.schedule_once(partial(cannon.carry_element, element))

    def element_vs_bottom(self, __space, arbiter):
        e, bo = arbiter.shapes
        if e.collision_type == defs.BOTTOM_BOUND:
            e, bo = bo, e

        e = self.bodyobjects[e.body]
        self.remove_obj(e)

    def element_vs_element(self, __space, arbiter):
        e1, e2 = [self.bodyobjects[s.body] for s in arbiter.shapes]

        # Clock.schedule_once(partial(e1.collide_with_another,e2))
        return e1.collide_with_another(e2)

    def wizard_vs_bottom(self, __space, arbiter):
        wiz, bo = arbiter.shapes
        if wiz.collision_type == defs.BOTTOM_BOUND:
            wiz, bo = bo, wiz

        __mw, mh = defs.map_size
        self.add_widget(GameOver(pos=(400, mh), size=(600, 150)))
        App.get_running_app().sm.schedule_gameover()

    def on_key_up(self, window, key, *largs, **__kwargs):
        code = Keyboard.keycode_to_string(None, key)
        self.keys_pressed.remove(code)

    def on_key_down(self, window, key, *largs, **kwargs):
        # very dirty hack, but: we don't have any instance of keyboard anywhere, and
        # keycode_to_string should be in fact classmethod, so passing None as self is safe
        code = Keyboard.keycode_to_string(None, key)
        self.keys_pressed.add(code)

        if code == 'spacebar':
            if not self.wizard.release_element():
                self.cannon.shoot()

    def on_touch_move(self, touch):
        if touch.is_double_tap:
            return

        dx, dy = touch.dx, touch.dy
        ix = defs.wizard_touch_impulse_x
        if abs(dx) > abs(dy):
            Logger.debug("horizontal")
            self.wizard.body.apply_impulse((ix * dx, 0))

        if abs(dy) > abs(dx):
            Logger.debug("vertical")
            self.cannon.aim += dy/2

    def on_touch_down(self, touch):
        if touch.is_double_tap:
            if not self.wizard.release_element():
                self.cannon.shoot()

    def on_touch_up(self, touch):
        self.keys_pressed.clear()

    def on_resize(self, win, w, h):
        mw, mh = defs.map_size
        xratio = w/mw
        yratio = h/mh

        self.scale = min(xratio, yratio)
        Logger.debug("self.scale = %s", self.scale)

    def update(self, dt):
        self.update_space()

        mi, ma = defs.num_elements_in_zone
        n = self.num_elements_in_zone
        if n < mi:
            Logger.debug("drop because num elements is below %s", mi)
            self.drop_element()

        if random.random() < defs.drop_chance and n < ma:
            self.drop_element()

        for o in self.children:
            if isinstance(o, AnimObject):
                o.update(dt)

        for o in self.oo_to_remove:
            self.remove_obj(o, just_schedule=False)
            Logger.debug("%s just removed", o)
            assert o not in self.children
        self.oo_to_remove.clear()

        for ocl, oa, okw in self.oo_to_add:
            newo = ocl(*oa, **okw)
            Logger.debug("newo %s created", newo)
            self.add_widget(newo)
        self.oo_to_add.clear()

        if 'up' in self.keys_pressed:
            self.cannon.aim += 1.5
        if 'down' in self.keys_pressed:
            self.cannon.aim -= 1.5

        dx = 0
        if 'left' in self.keys_pressed:
            dx -= 10
        if 'right' in self.keys_pressed:
            dx += 10
        if dx:
            self.wizard.body.apply_impulse((defs.wizard_touch_impulse_x * dx, 0))

    def drop_element(self):
        """ drop element from heaven """
        w, h = self.size

        # get proper x coordinate
        x = random.randint(*defs.drop_zone)

        element = Element.random(center=(x, h))
        if not element:
            return
        self.add_widget(element)
        self.num_elements_in_zone += 1
