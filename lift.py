# -*- coding: utf-8 -*-
import time
from threading import Thread, Event


class MyThread(Thread):
    def __init__(self, parent, init_func, loop_func, stop_evt=None):
        Thread.__init__(self)
        self.parent = parent
        self.init_func = init_func
        self.loop_func = loop_func
        self.stop_evt = stop_evt

    def run(self):
    	self.init_func(self, self.parent)
        while not self.stop_evt.is_set():
            self.loop_func(self, self.parent)

class Lift:
	def __init__(self, levels, initial_level, break_length):
		self.levels = levels
		self.level = initial_level
		self.real_level = initial_level
		self.target_level = None
		self.break_length = break_length
		self.inside_requests = set()
		self.outside_up_requests = set()
		self.outside_down_requests = set()
		self.stop = True
		self.up = True
		self.hold = False
		self.to_power_off = False
		self._display_thr = None
		self._display_stop_evt = Event()
		self._engine_thr = None
		self._engine_stop_evt = Event()
		self._controller_thr = None
		self._controller_stop_evt = Event()
		print('[INFO] \tLift built')

	def select_new_target(self):
		try:
			upper = min([i for i in self.inside_requests if i >= self.level] 
				+ [i for i in self.outside_up_requests if i > self.level])
		except ValueError:
			try:
				upper = max([i for i in self.outside_down_requests if i > self.level])
			except ValueError:
				upper = None
		try:
			lower = max([i for i in self.inside_requests if i <= self.level]
				+ [i for i in self.outside_down_requests if i < self.level])
		except ValueError:
			try:
				lower = min([i for i in self.outside_up_requests if i < self.level])
			except ValueError:
				lower = None

		self.target_level = None
		if self.up:
			if upper is not None:
				self.target_level = upper
			elif lower is not None:
				self.target_level = lower
		else:
			if lower is not None:
				self.target_level = lower
			elif upper is not None:
				self.target_level = upper

	def power_on(self):
		print('[INFO] \tStart power-on routine')
		self.display_on()
		print('[INFO] \tDisplay on')
		self.engine_run()
		print('[INFO] \tEngine running')
		self.controller_run()
		print('[INFO] \tController running')
		print('[INFO] \tFully up')

	def power_off(self):
		print('[INFO] \tStart power-off routine')
		self.display_off()
		print('[INFO] \tDisplay off')
		self.engine_stop()
		print('[INFO] \tEngine stopped')
		self.controller_stop()
		print('[INFO] \tController stopped')
		print('[INFO] \tFully down')

	def display_on(self):
		def init_func(self, parent):
			time.sleep(1)
			print('[DISPLAY] \t{} {} \t({})'.format('A' if parent.up else 'V', parent.level, parent.target_level))
			self.last_display = parent.level

		def loop_func(self, parent):
			if parent.level != self.last_display:
				print('[DISPLAY] \t{} {} \t({})'.format('A' if parent.up else 'V', parent.level, parent.target_level))
				self.last_display = parent.level
			time.sleep(0.01)

		self._display_thr = MyThread(self, init_func, loop_func, self._display_stop_evt)
		self._display_thr.start()

	def display_off(self):
		if self._display_thr and not self._display_stop_evt.is_set():
			self._display_stop_evt.set()
			self._display_thr.join()

	def engine_run(self):
		def init_func(self, parent):
			pass

		def loop_func(self, parent):
			if parent.target_level is None:
				parent.stop = True
				time.sleep(0.1)
				return
			elif parent.real_level < parent.target_level:
				parent.stop = False
				parent.up = True
				time.sleep(1)
				parent.real_level += 1
			elif parent.real_level > parent.target_level:
				parent.stop = False
				parent.up = False
				time.sleep(1)
				parent.real_level -= 1

			if parent.real_level in parent.levels:
				parent.level = parent.real_level
				if parent.level == parent.target_level:
					parent.stop = True
					parent.inside_requests -= {parent.level}
					if parent.up:
						parent.outside_up_requests -= {parent.level}
					else:
						parent.outside_down_requests -= {parent.level}
					time.sleep(1)
					print('[INFO] \tDoor {} opening'.format(parent.level))
					time.sleep(3)
					while parent.hold:
						time.sleep(1)
					print('[INFO] \tDoor {} closing'.format(parent.level))
					time.sleep(1)
					parent.select_new_target()
					if parent.target_level > parent.level:
						parent.up = True
						parent.outside_up_requests -= {parent.level}
					elif parent.target_level < parent.level:
						parent.up = False
						parent.outside_down_requests -= {parent.level}

		self._engine_thr = MyThread(self, init_func, loop_func, self._engine_stop_evt)
		self._engine_thr.start()

	def engine_stop(self):
		if self._engine_thr and not self._engine_stop_evt.is_set():
			self._engine_stop_evt.set()
			self._engine_thr.join()

	def controller_run(self):
		def init_func(self, parent):
			pass

		def loop_func(self, parent):
			if parent.to_power_off:
				time.sleep(0.01)
				return

			def process_new_request(t, parent, requests, request_type):
				if t not in parent.levels:
					print('[OPERATION] \trequest out of range, valid levels: {}'.format(parent.levels))
				else:
					if t in requests:
						if t != parent.target_level:
							requests.remove(t)
							print('[OPERATION] \t{} {} cancelled\n'
								'inside requests: {}\n'
								'outside up requests: {}\n'
								'outside down requests: {}\n'.format(request_type,
									t,
									sorted(parent.inside_requests),
									sorted(parent.outside_up_requests),
									sorted(parent.outside_down_requests)))
						else:
							print('[OPERATION] \t{} {} can not be cancelled\n'
								'inside requests: {}\n'
								'outside up requests: {}\n'
								'outside down requests: {}\n'.format(request_type,
									t,
									sorted(parent.inside_requests),
									sorted(parent.outside_up_requests),
									sorted(parent.outside_down_requests)))
					else:
						requests.add(t)
						print('[OPERATION] \t{} {} added\n'
							'inside requests: {}\n'
							'outside up requests: {}\n'
							'outside down requests: {}\n'.format(request_type,
								t,
								sorted(parent.inside_requests),
								sorted(parent.outside_up_requests),
								sorted(parent.outside_down_requests)))
						parent.select_new_target()

			t = raw_input('')
			if t.isdigit():
				t = int(t)
				process_new_request(t, parent, parent.inside_requests, 'inside_request')
			elif len(t) > 1 and t[:-1].isdigit():
				if t[-1] == 'u':
					t = int(t[:-1])
					process_new_request(t, parent, parent.outside_up_requests, 'outside_up_request')
				elif t[-1] == 'd':
					t = int(t[:-1])
					process_new_request(t, parent, parent.outside_down_requests, 'outside_down_request')
			elif t == 'h':
				parent.hold = True
				print('[OPERATION] \tdoor hold\n'
					'inside requests: {}\n'
					'outside up requests: {}\n'
					'outside down requests: {}\n'.format(
						sorted(parent.inside_requests),
						sorted(parent.outside_up_requests),
						sorted(parent.outside_down_requests)))
			elif t == 'r':
				parent.hold = False
				print('[OPERATION] \tdoor released\n'
					'inside requests: {}\n'
					'outside up requests: {}\n'
					'outside down requests: {}\n'.format(
						sorted(parent.inside_requests),
						sorted(parent.outside_up_requests),
						sorted(parent.outside_down_requests)))
			elif t == 'off':
				parent.hold = False
				parent.to_power_off = True

		self._controller_thr = MyThread(self, init_func, loop_func, self._controller_stop_evt)
		self._controller_thr.start()

	def controller_stop(self):
		if self._controller_thr and not self._controller_stop_evt.is_set():
			self._controller_stop_evt.set()
			self._controller_thr.join()


if __name__ == '__main__':
	lift = Lift(range(13)+range(15,21), 10, 2)
	lift.power_on()
	while not lift.to_power_off:
		time.sleep(0.1)
	lift.power_off()
