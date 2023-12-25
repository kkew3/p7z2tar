#!/usr/bin/env python3
import typing as ty
import tarfile
import argparse
import sys

import libarchive
from tqdm import tqdm


def tarinfo_from_libarchive_entry(entry):
    """
    Build a ``TarInfo`` object from a libarchive entry. Besides name, size
    and mtime attributes are also set.

    :param entry: the libarchive entry
    :return: the built TarInfo
    """
    ti = tarfile.TarInfo(str(entry))
    ti.size = entry.size
    if entry.mtime:
        ti.mtime = entry.mtime
    if entry.mode:
        ti.mode = entry.mode
    return ti


class ArchiveEntryBlocks(ty.BinaryIO):
    """
    Buffered IO that reads directly from blocks of an entry without additional
    copy.
    """
    def __init__(self, blocks: ty.Iterator[bytes]):
        """
        :param blocks: to get blocks from a libarchive entry, use
               ``iter(entry.get_blocks())``
        """
        self.blocks = blocks
        self.curr_block = None
        self.cursor = None

    def read(self, size=-1, /) -> bytes:
        if size is None:
            size = -1
        if size < 0:
            return self._read_all()
        if size == 0:
            return b''
        cbuf = []
        retrieved_size = 0
        while retrieved_size < size:
            if self.cursor is None:
                try:
                    self.curr_block = next(self.blocks)
                except StopIteration:
                    break
                prev_cursor = len(self.curr_block)
            else:
                prev_cursor = self.cursor
            self.cursor = retrieved_size + prev_cursor - size
            if self.cursor <= 0:
                self.cursor = None
                cbuf.append(self.curr_block[-prev_cursor:])
                retrieved_size += prev_cursor
            else:
                # Since retrieved_size < size due to the while condition, by
                # `self.cursor = retrieved_size + prev_cursor - size`, it must
                # be true that self.cursor < prev_cursor. Therefore, this line
                # holds.
                cbuf.append(self.curr_block[-prev_cursor:-self.cursor])
                retrieved_size += prev_cursor - self.cursor
        return b''.join(cbuf)

    def _read_all(self):
        return b''.join(self.blocks)


def test_archive_entry_blocks():
    blocks = ArchiveEntryBlocks(iter([b'h', b'el', b'lo ', b'world']))
    assert blocks.read() == b'hello world'
    blocks = ArchiveEntryBlocks(iter([b'h', b'el', b'lo ', b'world']))
    assert blocks.read(1) == b'h'
    assert blocks.read(2) == b'el'
    assert blocks.read() == b'lo world'
    blocks = ArchiveEntryBlocks(iter([b'h', b'el', b'lo ', b'world']))
    assert blocks.read(2) == b'he'
    assert blocks.read(2) == b'll'
    blocks = ArchiveEntryBlocks(iter([b'h', b'el', b'lo ', b'world']))
    assert blocks.read(3) == b'hel'
    assert blocks.read(4) == b'lo w'
    blocks = ArchiveEntryBlocks(iter([b'h', b'el', b'lo ', b'world']))
    assert blocks.read(4) == b'hell'
    assert blocks.read(5) == b'o wor'
    assert blocks.read(5) == b'ld'
    assert blocks.read(2) == b''


def make_parser():
    parser = argparse.ArgumentParser(
        description='Write 7z file to /dev/stdout as a tar stream.')
    parser.add_argument(
        '-p',
        '--show-progress',
        action='store_true',
        help=('note that an extra iteration over the 7z archive is required '
              'to fetch the number of files in it, unless `-T <file>` is '
              'specified'))
    parser.add_argument(
        '-T',
        '--files-from',
        help=('extract paths in the archive only from this list '
              '(one per line), with `-` means /dev/stdin; note that even if '
              'the paths are given from /dev/stdin, all paths are read into '
              'memory before starting to stream the archive'))
    parser.add_argument(
        '-Z',
        '--compressed',
        choices=['gz', 'bz2', 'xz'],
        help='write to /dev/stdout compressed stream directly')
    parser.add_argument(
        'archive_files',
        metavar='ARCHIVE_FILE',
        nargs='+',
        help=('if more than one ARCHIVE_FILEs are provided, '
              'the tar stream will be concatenated, and you will need to '
              'ensure yourself that the ARCHIVE_FILEs contain disjoint file '
              'paths'))
    return parser


def extract_to_stdout(
    archive_files: ty.List[str],
    files_from: ty.Optional[str],
    show_progress: bool,
    compressed: ty.Optional[str],
):
    if files_from == '-':
        files_from_list = set(f.rstrip('\n') for f in sys.stdin)
    elif files_from:
        with open(files_from, encoding='utf-8') as infile:
            files_from_list = set(f.rstrip('\n') for f in infile)
    else:
        files_from_list = None

    if show_progress and files_from_list:
        total = len(files_from_list)
    elif show_progress:
        total = 0
        for file in archive_files:
            with libarchive.file_reader(file) as z:
                total += sum(1 for _ in z)
    else:
        total = 0

    if not compressed:
        compressed = ''
    mode = f'w|{compressed}'

    with tqdm(desc='p7z2tar', total=total, disable=not show_progress) as prog, \
         tarfile.open(mode=mode, fileobj=sys.stdout.buffer) as tar:
        if files_from_list:
            for file in archive_files:
                with libarchive.file_reader(file) as z:
                    for entry in z:
                        if str(entry) not in files_from_list:
                            prog.update()
                            continue
                        ti = tarinfo_from_libarchive_entry(entry)
                        tar.addfile(
                            ti, ArchiveEntryBlocks(iter(entry.get_blocks())))
                        prog.update()
        else:
            for file in archive_files:
                with libarchive.file_reader(file) as z:
                    for entry in z:
                        ti = tarinfo_from_libarchive_entry(entry)
                        tar.addfile(
                            ti, ArchiveEntryBlocks(iter(entry.get_blocks())))
                        prog.update()


def main():
    args = make_parser().parse_args()
    extract_to_stdout(args.archive_files, args.files_from, args.show_progress,
                      args.compressed)


if __name__ == '__main__':
    main()
