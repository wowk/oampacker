import json
import sys

class PackerBuffer:
    def __init__(self):
        self.ops = {
            "mac": self.__parse_mac,
            "hex": self.__parse_hex,
            "int": self.__parse_int,
            "byte": self.__parse_byte,
            "bit": self.__parse_bit
        }
        self.bytes = []
        self.bits = []
        self.bits_count = 0

    def push(self, type, len, data):
        if type not in self.ops:
            raise Exception('unknown data type: %s' % type)
        print('type: %s, len: %s, data: %s' % (type, len, data))
        self.ops[type](len, data)

    def __parse_bit(self, len, data):
        pass

    def __parse_mac(self, len, data):
        pass

    def __parse_hex(self, len, data):
        pass

    def __parse_int(self, len, data):
        pass

    def __parse_byte(self, len, data):
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
        return self.__pack_list(desc)

    def __pack_dict(self, desc, use_default=False):
        self.__update_found_counter(desc)

        if 'len' in desc and desc['len'] > 0:
            if use_default is True:
                if desc['data'] == '':
                    raise Exception('')
                else:
                    self.buf.push(desc['type'], desc['len'], desc['data'])
                    #print('%s = %s' % (desc['name'], desc['data']))
            else:
                arg = self.__next()
                if arg.startswith('--') is True:
                    if desc['data'] == '':
                        raise Exception('')
                    else:
                        self.buf.push(desc['type'], desc['len'], desc['data'])
                        #print('%s = %s' % (desc['name'], desc['data']))
                        self.__back()
                else:
                    self.buf.push(desc['type'], desc['len'], arg)
                    #print('%s = %s' % (desc['name'], arg))

        if 'sub' in desc:
            return self.__pack_list(desc['sub'])
        else:
            return desc['len']

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
        #print(ctrl)
        padding = ctrl['padding']
        if padding != 'none':
            padding_len = desc[0]['len']

        for d in desc:
            if d['name'] == arg:
                ret = self.__pack_dict(d)
                return ret
        else:
            raise Exception('unknown option %s' % arg)

    def __chose_all_by_order(self, ctrl, desc):
        arg = self.__option()
        if len(arg) == 0:
            raise Exception('need at least one option after %s' % self.__previous())

        for d in desc:
            if d['name'] == arg:
                self.__pack_dict(d)
                arg = self.__option()
            else:
                self.__pack_dict(d, use_default=True)
        else:
            if arg != '':
                self.__back()
        return True

    def __chose_all_without_order(self, ctrl, desc):
        arg = self.__option()
        options = [key['name'] for key in desc]
        while True:
            for d in desc:
                if arg == d['name']:
                    self.__pack_dict(d)
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

    def __chose_multi_by_order(self, ctrl, desc):
        arg = self.__option()

        for d in desc:
            while True:
                if arg == d['name']:
                    self.__pack_dict(d)
                    arg = self.__option()
                    if len(arg) == 0:
                        break
                elif d['optional'] is False:
                    self.__pack_dict(d)
                    break
                self.__reset_found_counter(d)
        else:
            if len(arg) != 0:
                self.__back()

    def __chose_multi_without_order(self, ctrl, desc):
        arg = self.__option()

        options = {desc[i]['name']: i for i in range(len(desc))}
        not_optional = [d['name'] for d in desc if d['optional'] is False]
        while True:
            if arg in options:
                self.__pack_dict(desc[options[arg]])
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


p = PacketPacker('cmd.json')
p.pack()
