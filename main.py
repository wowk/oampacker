import re
import sys
import json
from socket import htons,htonl

class Padding:
	def __init__(self, ctrl):
		self.__type = ctrl['padding']
		self.__bytes = 0
		self.__counts = 0
		self.__len = 0
		if self.__type == 'none':
			self.__bytes = 0
			self.__counts = 0
			self.__len = 0
		else:
			self.__bytes += ctrl['base']
			self.__counts += ctrl['base']
			self.__len = ctrl['len']

	def update_padding(self, ret):
		if self.__type == 'bytes':
			self.__bytes += ret
		elif self.__type == 'counts':
			self.__counts += 1
		else:
			self.__bytes += ret

	def bytes(self):
		return self.__bytes

	def data(self):
		if self.__type == 'bytes':
			return 'int', self.__len, self.__bytes
		elif self.__type == 'counts':
			return '-int', self.__len, self.__counts
		else:
			return 'int', 0, 0

class PackerBuffer:
	mac_pattern = '([a-fA-F0-9]{2}[:]){5}[a-fA-F0-9]{2}|[a-fA-F0-9]{12}'
	hex_pattern = '0x[a-fA-F0-9]{1,}'
	byte_pattern = '[a-fA-F0-9]{2,}'
	int_pattern = '[0-9]{1,}'
	def __init__(self):
		self.ops = {
			"mac": self.__parse_mac,
			"hex": self.__parse_hex,
			"int": self.__parse_int,
			"byte": self.__parse_byte,
			"bit": self.__parse_bit
		}
		self.items = []
		self.byte_array = []

	def add_padding(self, ctrl):
		padding =  Padding(ctrl)
		self.items.append(padding)
		return padding

	def push(self, type, size, data):
		if type not in self.ops:
			raise Exception('unknown data type: %s' % type)
		#print('type: %s, len: %s, data: %s' % (type, len, data))
		self.items.append((type, size, self.ops[type](size, data),))

	def __parse_bit(self, size, data):
		return data

	def __parse_mac(self, sz, data):
		data = data.strip()
		if re.fullmatch(PackerBuffer.mac_pattern, data) is None:
			raise Exception('')
		elif ':' in data:
			data = data.replace(':', '')
		return bytes.fromhex(data)

	def __parse_hex(self, sz, data):
		if re.fullmatch(PackerBuffer.hex_pattern, data) is None:
			raise Exception('%s is not a hex value' % data)
		data = data[2:].lstrip('0')

		if sz > 4 or (len(data)/2 > sz):
			raise Exception('0x%s is out of range')
		data = data.ljust(sz * 2, '0')
		if sz == 1:
			return bytes.fromhex(data)
		else:
			lst = [data[i:i + 2] for i in range(0, sz * 2, 2)]
			lst.reverse()
			data = ''
			for b in lst:
				data += b
		return bytes.fromhex(data)

	def __parse_int(self, size, data):
		try:
			data = hex(int(data))[2:]
		except ValueError:
			print(data)
			raise Exception('')
		if len(data)/2 > size:
			print(data, size)
			raise Exception('')
		data = data.ljust(size*2, '0')
		lst = [data[i:i+2] for i in range(0, size*2, 2)]
		lst.reverse()
		data = ''
		for b in lst:
			data += b
		print(data, lst)
		return bytes.fromhex(data)

	def __parse_byte(self, size, data):
		if re.fullmatch(PackerBuffer.byte_pattern, data) is None:
			raise Exception('')
		elif len(data)/2 > size:
			raise Exception('')
		print('========', data)
		data = data.rjust(size * 2, '0')
		print('========', data)
		return bytes.fromhex(data)

	def to_byte_array(self):
		pass


class PacketPacker:
	def __init__(self, json_file):
		self.arg = sys.argv
		self.index = 1
		with open(json_file) as fp:
			self.desc = json.load(fp)
		self.buf = PackerBuffer()

	def __peek(self):
		if self.index < len(self.arg):
			return self.arg[self.index]
		else:
			return ''

	def __previous(self):
		if self.index > 0:
			self.index -= 1
		return self.__next()

	def __next(self):
		if self.index < len(self.arg):
			arg = self.arg[self.index]
			self.index += 1
		else:
			arg = ''
		return arg

	def __back(self):
		if self.index > 0:
			self.index -= 1

	def pack(self):
		return self.__pack(self.desc)


	def __reset_found_counter(self, obj):
		if isinstance(obj, dict) is True:
			if 'found' in obj:
				obj['found'] = 0
			if 'sub' in obj:
				self.__reset_found_counter(obj['sub'])
		elif isinstance(obj, list):
			if obj[0]['chose'] != 'multi':
				for d in obj:
					self.__reset_found_counter(d)

	@staticmethod
	def __update_found_counter(desc):
		if 'max' in desc:
			if desc['found'] < desc['max']:
				desc['found'] += 1
			else:
				raise Exception(desc['name'])

	def __pack(self, desc):
		len = self.__pack_list(desc)
		print(len)
		return self.buf

	def __pack_dict(self, desc, use_default=False):
		self.__update_found_counter(desc)

		len = 0
		if 'len' in desc and desc['len'] > 0:
			len += desc['len']
			if use_default is True:
				if desc['data'] == '':
					raise Exception('')
				else:
					self.buf.push(desc['type'], desc['len'], desc['data'])
					print('%s = %s' % (desc['name'], desc['data']))
			else:
				arg = self.__next()
				if arg.startswith('--') is True:
					if desc['data'] == '':
						raise Exception('')
					else:
						self.buf.push(desc['type'], desc['len'], desc['data'])
						print('%s = %s' % (desc['name'], desc['data']))
						self.__back()
				else:
					self.buf.push(desc['type'], desc['len'], arg)
					print('%s = %s' % (desc['name'], arg))

		if 'sub' in desc:
			len += self.__pack_list(desc['sub'])
		return len

	def __option(self):
		arg = self.__next()
		if arg.startswith('--') is True:
			arg = arg[2:]
		elif len(arg) != 0:
			raise Exception('argument %s is not an option' % arg)
		return arg

	def __chose_one(self, ctrl, desc):
		arg = self.__option()
		if len(arg) == 0:
			raise Exception('need at least one option after %s' % self.__previous())

		padding = self.buf.add_padding(ctrl)

		for d in desc:
			if d['name'] == arg:
				ret = self.__pack_dict(d)
				padding.update_padding(ret)
				break
		else:
			raise Exception('unknown option %s' % arg)

		return padding.bytes()

	def __chose_all_by_order(self, ctrl, desc):
		arg = self.__option()
		if len(arg) == 0:
			raise Exception('need at least one option after %s' % self.__previous())

		padding = self.buf.add_padding(ctrl)
		for d in desc:
			if d['name'] == arg:
				ret = self.__pack_dict(d)
				padding.update_padding(ret)
				arg = self.__option()
			else:
				ret = self.__pack_dict(d, use_default=True)
				padding.update_padding(ret)
		else:
			if arg != '':
				self.__back()

		return padding.bytes()

	def __chose_all_without_order(self, ctrl, desc):
		arg = self.__option()
		options = [key['name'] for key in desc]
		padding = self.buf.add_padding(ctrl)

		while True:
			for d in desc:
				if arg == d['name']:
					ret = self.__pack_dict(d)
					padding.update_padding(ret)
					if arg in options:
						options.remove(arg)
					break
			else:
				self.__back()
				if len(options) != 0:
					raise Exception('')
				else:
					break
			arg = self.__option()

		return padding.bytes()

	def __chose_multi_by_order(self, ctrl, desc):
		arg = self.__option()
		padding = self.buf.add_padding(ctrl)

		for d in desc:
			while True:
				if arg == d['name']:
					ret = self.__pack_dict(d)
					padding.update_padding(ret)
					arg = self.__option()
					if len(arg) == 0:
						break
				elif d['optional'] is False:
					ret = self.__pack_dict(d)
					padding.update_padding(ret)
					break
				self.__reset_found_counter(d)
		else:
			if len(arg) != 0:
				self.__back()

		return padding.bytes()

	def __chose_multi_without_order(self, ctrl, desc):
		arg = self.__option()
		options = {desc[i]['name']: i for i in range(len(desc))}
		not_optional = [d['name'] for d in desc if d['optional'] is False]
		padding = self.buf.add_padding(ctrl)

		while True:
			if arg in options:
				ret = self.__pack_dict(desc[options[arg]])
				padding.update_padding(ret)
				self.__reset_found_counter(desc[options[arg]])
				if arg in not_optional:
					not_optional.remove(arg)
			else:
				if arg != '':
					self.__back()
				if len(not_optional) != 0:
					raise Exception('')
				else:
					break
			arg = self.__option()
		return padding.bytes()

	def __pack_list(self, desc):
		if len(desc) < 1 or desc[0]['name'] != 'ctrl':
			raise Exception('')

		order = desc[0]['order']
		chose = desc[0]['chose']
		ctrl = desc[0]
		desc = desc[1:]

		if chose == 'one':
			ret = self.__chose_one(ctrl, desc)
		elif chose == 'all':
			if order is True:
				ret = self.__chose_all_by_order(ctrl, desc)
			else:
				ret = self.__chose_all_without_order(ctrl, desc)
		elif chose == 'multi':
			if order is True:
				ret = self.__chose_multi_by_order(ctrl, desc)
			else:
				ret = self.__chose_multi_without_order(ctrl, desc)
		else:
			raise Exception('')

		return ret


p = PacketPacker('cmd.json')
items = p.pack().items
for item in items:
	if isinstance(item, Padding):
		print(item.data())
	else:
		print(item)