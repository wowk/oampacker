import json
import sys


class PacketPacker:
	def __init__(self, json_file):
		self.arg = sys.argv[1:]
		self.index = 0

	def peek(self):
		if self.index < len(self.arg):
			return self.arg[self.index]
		else:
			return ''

	def next(self):
		if self.index < len(self.arg):
			ret = self.arg[self.index]
			self.index += 1
		else:
			ret = ''
		return ret

	def back(self):
		if self.index > 0:
			self.index -= 1

	def pack(self):
		pass

	def __pack(self, desc):
		return self.__pack_list(desc)
	"""
	        {
                "name": "flags",
                "optional": 0,
                "max": 1,
                "found": 0,
                "type": "byte",
                "len": 1,
                "data": "0xFF"
            },
	"""
	def __pack_dict(self, desc, use_default=True):
		if desc['found'] < desc['max']:
			desc['found'] += 1
		else:
			raise Exception('')

		if 'len' in desc and desc['len'] > 0:
			arg = self.next()
			if arg.startswith('--') is True:
				if desc['data'] == '':
					raise Exception('')
				else:
					self.back()
					pass
			else:
				print(arg)
				pass

		if 'sub' in desc:
			return self.__pack_list(desc['sub'])

		return True

	def __pack_list(self, desc):
		order = desc[0]['order']
		chose = desc[0]['chose']

		desc = desc[1:]

		arg = self.next()
		if arg.startswith('--') is False:
			raise Exception('')
		else:
			arg = arg[2:]

		if chose == 'one':
			for d in desc:
				if d['name'] == arg:
					return self.__pack_dict(d, )

		elif chose == 'any':
			for d in desc:
				if d['name'] == arg:
					arg = self.next()[2:]
					if arg == '':
						raise Exception('')
				self.__pack_dict(d)
			return True
		elif chose == 'multi':
			not_optional = [item['name'] for item in desc if item['optional'] is True]
			optional = [item['name'] for item in desc if item['optional'] is False]
			index = {desc[i]['name']: i for i in range(len(desc))}
		else:
			raise Exception('')