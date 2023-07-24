from __future__ import annotations

from krawl.log import get_child_logger
from krawl.normalizer.github import GitHubFileHandler

log = get_child_logger("github")

BASE_URL='https://github.com'
SLUG='OPEN-NEXT/OKH-LOSH'
FILE_RELATIVE_PATH='.gitignore'
DEV_BRANCH='master'
VERSION='v1.1.0'
FILE_WEB_URL='https://github.com/OPEN-NEXT/OKH-LOSH/blob/master/.gitignore'
FILE_DL_URL='https://github.com/OPEN-NEXT/OKH-LOSH/raw/master/.gitignore'
FILE_FROZEN_WEB_URL='https://github.com/OPEN-NEXT/OKH-LOSH/blob/v1.1.0/.gitignore'
FILE_FROZEN_DL_URL='https://github.com/OPEN-NEXT/OKH-LOSH/raw/v1.1.0/.gitignore'

import unittest

class TestStringMethods(unittest.TestCase):

    def test_is_frozen_url(self):
        file_handler = GitHubFileHandler()
        proj_info = file_handler.gen_proj_info_raw(SLUG, VERSION, DEV_BRANCH)
        self.assertTrue(file_handler.is_frozen_url(proj_info, FILE_FROZEN_DL_URL))
        self.assertFalse(file_handler.is_frozen_url(proj_info, FILE_DL_URL))

    def test_to_url(self):
        file_handler = GitHubFileHandler()
        proj_info = file_handler.gen_proj_info_raw(SLUG, VERSION, DEV_BRANCH)
        self.assertTrue(file_handler.to_url(proj_info, FILE_RELATIVE_PATH, True), FILE_FROZEN_DL_URL)
        self.assertTrue(file_handler.to_url(proj_info, FILE_RELATIVE_PATH, False), FILE_DL_URL)

    def test_extract_path(self):
        file_handler = GitHubFileHandler()
        proj_info = file_handler.gen_proj_info_raw(SLUG, VERSION, DEV_BRANCH)
        self.assertTrue(file_handler.extract_path(proj_info, FILE_FROZEN_DL_URL), FILE_RELATIVE_PATH)
        self.assertTrue(file_handler.extract_path(proj_info, FILE_DL_URL), FILE_RELATIVE_PATH)

    def test__extract_slug(self):
        file_handler = GitHubFileHandler()
        proj_info = file_handler.gen_proj_info_raw(SLUG, VERSION, DEV_BRANCH)
        self.assertEqual(file_handler._extract_slug(FILE_FROZEN_DL_URL), SLUG)

if __name__ == '__main__':
    unittest.main()