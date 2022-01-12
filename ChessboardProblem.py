"""
Internal chessboard: array of length 64 containing 1s and 0s corresponding to the flipped items
A chessboard layout has a number associated with it:
    that number, in binary, has each digit corresponding to the parity of all the chessboard flip states of positions
    whose binary number has a 1 in that digit. For example, that number will be even if there is even parity among
    all odd positions, and odd if there is odd parity among all odd positions. The parity off all groups is efficiently
    calculated by simply XORing all position numbers that hold a 1 in the chessboard.
The first person knows the chessboard number (computing it from what is visible) and the target number that it should
be, so as to tell the position of the key. XORing those numbers together produces a binary number with ones in each
digit corresponding to a parity group that must be changed, and flipping that number affects just those parity groups,
so as to change the board number to the target.
"""

from functools import reduce
import numpy as np

CHESSBOARD_ROW = '87654321'
CHESSBOARD_COL = 'abcdefgh'


def _chessboard_number(chessboard):
    return reduce(lambda x, y: x ^ y, [position for position in range(64) if chessboard[position] == 1])


def make_flip(chessboard, key_location, comments=False):
    current_number = _chessboard_number(chessboard)
    target_number = key_location
    flip_position = current_number ^ target_number
    if comments:
        print(f"flipping {pos_to_coord(flip_position)}")
    chessboard[flip_position] ^= 1
    return chessboard


def find_key(chessboard):
    return _chessboard_number(chessboard)


def print_board(chessbaord):
    # print the column headings
    print("  ", " ".join([letter for letter in CHESSBOARD_COL]))

    for row in range(8):
        # print the row heading, and the board row
        print(CHESSBOARD_ROW[row] + ":", " ".join([str(i) for i in chessbaord[row * 8: (row + 1) * 8]]))


def pos_to_coord(pos):
    number = CHESSBOARD_ROW[pos // 8]
    letter = CHESSBOARD_COL[pos % 8]
    return letter + number


def main():
    chessboard = np.random.randint(2, size=64)
    key_pos = np.random.randint(64)

    print(f"Initial random chessboard layout, with key hidden under {pos_to_coord(key_pos)}")
    print_board(chessboard)
    chessboard = make_flip(chessboard, key_pos, comments=True)

    print("Chessboard now looks like")
    print_board(chessboard)
    print(f"So the key must be under {pos_to_coord(find_key(chessboard))}")


if __name__ == '__main__':
    main()
    