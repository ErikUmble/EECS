import math
import random
from functools import reduce


def rect_parity_encode(data, num_rows, num_cols):
    """:return a list of size len(data) + num_rows + num_cols in the form [data, row_parity_bits, col_parity_bits]
        input data should be a list of 1s and 0s, of length num_rows * num_cols
    """
    assert len(data) == num_rows * num_cols
    codeword = data.copy()
    for row in range(num_rows):
        # appends the row parity bit (the mod 2 sum of the elements in the row)
        # could alternatively use functools.reduce(lambda i, j: i ^ j, data[row * num_cols]) for xor of all the elements
        # we assume rows are sequential elements
        codeword.append(sum(data[row * num_cols: (row + 1) * num_cols]) % 2)

    for col in range(num_cols):
        # similarly, appends the parity bit for the elements of the corresponding column
        codeword.append(sum(data[col: num_cols * num_rows: num_cols]) % 2)

    return codeword


def rect_parity_decode(codeword, num_rows, num_cols):
    """:return a list of size num_rows * num_cols of the data, correcting up to one error in it using the parity bits
        does not attempt to correct the data if it has multiple errors
        input codeword should be a list of size num_rows * num_cols + num_rows + num_cols containing 1s and 0s
    """
    data = codeword[: num_cols * num_rows].copy()
    row_parity_bits = codeword[num_cols * num_rows: num_cols * num_rows + num_rows]
    col_parity_bits = codeword[num_cols * num_rows + num_rows: num_cols * num_rows + num_cols + num_rows]
    row_error = -1
    col_error = -1

    # find the error
    for row in range(num_rows):
        # expression is 1 if parity error, 0 otherwise
        if (sum(data[row * num_cols: (row + 1) * num_cols]) % 2) ^ row_parity_bits[row]:
            if row_error >= 0:
                # send the data as-is if a second row error is discovered
                return data
            row_error = row

    for col in range(num_cols):
        if (sum(data[col: num_cols * num_rows: num_cols]) % 2) ^ col_parity_bits[col]:
            if col_error >= 0:
                return data
            col_error = col

    # fix the error if one was found
    if row_error >= 0 and col_error >= 0:
        data[(num_cols * row_error) + col_error] ^= 1  # flip the bit at the location specified by the errors
        return data
    else:
        # either was a parity bit error, or no error
        return data


def random_test_rect_parity(num_cols, num_rows, num_tests=100):

    def test_case(data):
        encoded = rect_parity_encode(data, num_rows, num_cols)
        for i in range(num_rows):
            for j in range(num_cols):
                # flip the bit of encoded, see if we can decode, then flip it back
                encoded[(num_cols * i) + j] ^= 1
                if rect_parity_decode(encoded, num_rows, num_cols) != data:
                    print(f"row {i} and col {j} \n {rect_parity_decode(encoded, num_rows, num_cols)} != {encoded}")
                    return False
                encoded[(num_cols * i) + j] ^= 1

        return True

    for case in range(num_tests):
        data = []
        for i in range(num_rows):
            for j in range(num_cols):
                data.append(random.randint(0, 1))
        if not test_case(data):
            return False
    return True


def random_test_hamming(block_size=16, num_tests=100):
    side_length = round(block_size ** 0.5)

    def test_case(data):
        encoded = hamming_encode(data, block_size)
        for i in range(side_length):
            for j in range(side_length):
                # flip the bit of encoded, see if we can decode, then flip it back
                encoded[(side_length * i) + j] ^= 1
                if hamming_decode(encoded, block_size) != data:
                    return False
                encoded[(side_length * i) + j] ^= 1

        return True

    for case in range(num_tests):
        data = []
        for pos in range(block_size - math.ceil(math.log2(block_size)) - 1):
            data.append(random.randint(0,1))
        if not test_case(data):
            return False
    return True


def hamming_encode_block(data, block_size=16):
    """ encodes data into a message block using the hamming code method
        adds an additional bit to the beginning (0th position) for position convenience, which is the total parity
    """
    side_length = round(block_size ** 0.5)
    num_parity_bits = round(math.log2(block_size))  # does not include the total parity bit
    assert(block_size ** 0.5 == side_length)  # ensure that we have a square block
    assert(num_parity_bits == math.log2(block_size))  # ensure that block size is a power of 2

    message = data.copy()
    # insert zeros into parity bit locations
    message.insert(0, 0)
    for i in range(num_parity_bits):
        message.insert(2 ** i, 0)
    assert(len(message) == block_size)

    # set the parity bits
    for i in range(num_parity_bits):
        # just the parity of all the positions that have a 1 in the same binary digit that the parity bit has
        message[2 ** i] = sum([message[j] for j in range(block_size) if j & (2 ** i)]) % 2
    # set the total parity bit
    message[0] = reduce(lambda x, y: x ^ y, [i for i in range(len(message)) if message[i]])

    return message


def hamming_encode(data, block_size=16):
    num_parity_bits = round(math.log2(block_size))  # does not include the total parity bit
    data_allocation = block_size - num_parity_bits - 1
    data = data.copy()

    # pad the data with zeros if necessary
    data += [0 for i in range(len(data) % data_allocation)]

    message = []
    for i in range(len(data) // data_allocation):
        message += hamming_encode_block(data[i * data_allocation: (i + 1) * data_allocation])

    return message


def hamming_decode_block(message):
    """ returns the data from a message block, correcting up to one error """

    num_parity_bits = round(math.log2(len(message)))
    # find the position of the error (assuming at most one) by parity checking all groups at once
    # this is the xor of all the positions that hold a 1 in the message
    error_pos = reduce(lambda x, y: x ^ y, [i for i in range(len(message)) if message[i]])
    data = message.copy()

    # flip the error (or the 0 pos bit if no error)
    data[error_pos] ^= 1

    # remove the parity bits (backwards so that removing a position does not change earlier positions)
    for i in range(num_parity_bits - 1, -1, -1):
        data.pop(2 ** i)
    data.pop(0)

    return data


def hamming_decode(message, block_size=16):
    """ decodes message into data by first splitting into blocks and decoding each block """
    data = []
    for i in range(len(message) // block_size):
        data += hamming_decode_block(message[i * block_size: (i+1) * block_size])

    return data


if __name__ == '__main__':
    pass

