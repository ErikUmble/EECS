TABLE_SIZE = 2**8


def init_table():
    """returns a list with the lowercase alphabet letters and space as entries"""
    table = [char for char in "abcdefghijklmnopqrstuvwxyz "]
    return table


def compress(text):
    """ :return list of int indices of compression table that correspond with text symbols """
    c_text = []
    table = init_table()
    string = ""
    for symbol in text:
        if string + symbol in table:
            string += symbol
        else:
            c_text.append(table.index(string))
            if len(table) > TABLE_SIZE:
                table = init_table()
            table.append(string + symbol)
            string = symbol
    c_text.append(table.index(string))

    return c_text


def decompress(compressed_text):
    text = []
    table = init_table()
    string = table[compressed_text[0]]
    for code in compressed_text:
        if len(table) <= code:
            entry = string + string[0]
        else:
            entry = table[code]
        text.append(entry)
        if len(table) > TABLE_SIZE:
            table = init_table()
        table.append(string + entry[0])
        string = entry

    return "".join(text)

if __name__ == '__main__':
    print(decompress(compress("hello how are you")))