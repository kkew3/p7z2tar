# p7z2tar

## Introduction

This utility writes 7z archive as tar stream to standard output.
No temporary disk space is needed.
The memory footprint is small.
The modification time and permission mode are preserved.

## Dependencies

- `libarchive`, and its python-binding `python-libarchive-c`
- `tqdm`, used to display progress bar

Test dependency:

- `pytest`, used to run tests

## Installation

### conda

First, optionally remove the `pytest` dependency in `environment.yaml`.

```bash
conda env create -f environment.yaml
conda activate p7z2tar
pip install .
```

### virtualenv

First, ensure `libarchive` has been installed.
For example, in macOS via [`brew`](https://brew.sh),

```bash
brew install libarchive
```

Then,

```bash
python3 -m virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
pip install .
```

## Usage

In the activated conda/virtualenv environment, run the following to print the usage:

```bash
p7z2tar.py --help
```

Quoted below:

```
usage: p7z2tar.py [-h] [-p] [-T FILES_FROM] [-Z {gz,bz2,xz}] ARCHIVE_FILE

Write 7z file to /dev/stdout as a tar stream.

positional arguments:
  ARCHIVE_FILE

options:
  -h, --help            show this help message and exit
  -p, --show-progress   note that an extra iteration over the 7z archive is
                        required to fetch the number of files in it, unless
                        `-T <file>` is specified
  -T FILES_FROM, --files-from FILES_FROM
                        extract paths in the archive only from this list (one
                        per line), with `-` means /dev/stdin; note that even
                        if the paths are given from /dev/stdin, all paths are
                        read into memory before starting to stream the archive
  -Z {gz,bz2,xz}, --compressed {gz,bz2,xz}
                        write to /dev/stdout compressed stream directly
```

Example:

```bash
p7z2tar.py -p archive.7z | gzip > archive.tar.gz
```

## Known issue

Symbolic link in 7z archive may not be handled correctly.

## For developer

To run tests, install `pytest`, and simply

```bash
pytest p7z2tar.py
```
