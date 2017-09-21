import json
import sys


class PacketPacker:
    def __init__(self, json_file):
        self.arg = sys.argv
        self.index = 1
        with open(json_file) as fp:
            self.desc = json.load(fp)

    def peek(self):
        if self.index < len(self.arg):
            return self.arg[self.index]
        else:
            return ''

    def previous(self):
        if self.index > 0:
            self.index -= 1
        return self.next()

    def next(self):
        if self.index < len(self.arg):
            arg = self.arg[self.index]
            self.index += 1
        else:
            arg = ''
        return arg

    def back(self):
        if self.index > 0:
            self.index -= 1

    def pack(self):
        return self.__pack(self.desc)

    def reset_found_counter(self, obj):
        if isinstance(obj, dict) is True:
            if 'found' in obj:
                obj['found'] = 0
            if 'sub' in obj:
                self.reset_found_counter(obj['sub'])
        elif isinstance(obj, list):
            if obj[0]['chose'] != 'multi':
                for d in obj:
                    self.reset_found_counter(d)

    def __pack(self, desc):
        return self.__pack_list(desc)

    def __pack_dict(self, desc, use_default=False):
        if 'max' in desc:
            if desc['found'] < desc['max']:
                desc['found'] += 1
            else:
                raise Exception(desc['name'])

        if 'len' in desc and desc['len'] > 0:
            if use_default is True:
                if desc['data'] == '':
                    raise Exception('')
                else:
                    print('%s = %s' % (desc['name'], desc['data']))
            else:
                arg = self.next()
                if arg.startswith('--') is True:
                    if desc['data'] == '':
                        raise Exception('')
                    else:
                        print('%s = %s' % (desc['name'], desc['data']))
                        self.back()
                else:
                    print('%s = %s' % (desc['name'], arg))

        if 'sub' in desc:
            return self.__pack_list(desc['sub'])

        return True

    def __pack_list(self, desc):

        if len(desc) < 1:
            return 0

        order = desc[0]['order']
        chose = desc[0]['chose']

        desc = desc[1:]

        arg = self.next()
        if arg.startswith('--') is True:
            arg = arg[2:]
        elif len(arg) != 0:
            raise Exception('argument %s is not an option' % arg)

        if chose == 'one':
            #必须指定一个选项
            if arg == '':
                raise Exception('need at least on option after %s' % self.previous())

            for d in desc:
                if d['name'] == arg:
                    return self.__pack_dict(d)
            else:
                raise Exception('unknown option %s' % arg)


        elif chose == 'all':
            #优默认值的选项可以不用指定，这样可以使用默认值
            if order is True:
                for d in desc:
                    if d['name'] == arg:
                        self.__pack_dict(d)
                        arg = self.next()
                        if arg.startswith('--') is True:
                            arg = arg[2:]
                        elif len(arg) != 0:
                            raise Exception('argument %s is not an option' % arg)
                    else:
                        self.__pack_dict(d, use_default=True)
                else:
                    if arg != '':
                        self.back()
                return True

            else:
                options = [key['name'] for key in desc]
                while True:
                    for d in desc:
                        if arg == d['name']:
                            self.__pack_dict(d)
                            if arg in options:
                                options.remove(arg)
                            break
                    else:
                        self.back()
                        if len(options) != 0:
                            raise Exception('')
                        else:
                            break
                    arg = self.next()
                    if arg.startswith('--') is True:
                        arg = arg[2:]
                    elif len(arg) != 0:
                        raise Exception('')

        elif chose == 'multi':
            if order is True:
                for d in desc:
                    while True:
                        if arg == d['name']:
                            self.__pack_dict(d)
                            arg = self.next()
                            if arg.startswith('--') is True:
                                arg = arg[2:]
                            elif len(arg) != 0:
                                raise Exception('')
                            else:
                                break
                        elif d['optional'] is False:
                            self.__pack_dict(d)
                            break
                        self.reset_found_counter(d)
                else:
                    if len(arg) != 0:
                        self.back()
            else:
                options = {desc[i]['name']:i for i in range(len(desc))}
                not_optional = [ d['name'] for d in desc if d['optional'] is False]
                while True:
                    if arg in options:
                        self.__pack_dict(desc[options[arg]])
                        self.reset_found_counter(desc[options[arg]])
                        if arg in not_optional:
                            not_optional.remove(arg)
                    else:
                        if arg != '':
                            self.back()
                        if len(not_optional) != 0:
                            raise Exception('')
                        else:
                            break
                    arg = self.next()
                    if arg.startswith('--') is True:
                        arg = arg[2:]
                    elif len(arg) != 0:
                        raise Exception('')
        else:
            raise Exception('')


p = PacketPacker('cmd.json')
p.pack()