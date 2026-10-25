import unittest

from code.authorization import authorizes_deletion


class AuthorizationTests(unittest.TestCase):
    def test_authorizes_direct_english_deletion_request(self):
        self.assertTrue(authorizes_deletion("Please delete my account and personal data."))

    def test_authorizes_deletion_request_written_in_spanish(self):
        self.assertTrue(
            authorizes_deletion(
                "Intenté eliminar mi cuenta ayer; completen la eliminación si hace falta."
            )
        )

    def test_authorizes_deletion_request_written_in_korean(self):
        self.assertTrue(authorizes_deletion("계정의 영구 삭제를 요청합니다."))

    def test_authorizes_deletion_request_written_in_portuguese(self):
        self.assertTrue(authorizes_deletion("Solicito a exclusão permanente da conta."))

    def test_authorizes_a_request_to_verify_prior_deletion_state(self):
        self.assertTrue(
            authorizes_deletion(
                "Please confirm that the profile is gone and remaining records cannot identify me."
            )
        )

    def test_rejects_access_request_that_explicitly_says_not_to_close_account(self):
        self.assertFalse(
            authorizes_deletion(
                "I can't access my profile and need help resetting the login. "
                "Do not close the account."
            )
        )

    def test_rejects_correction_request_without_record_removal(self):
        self.assertFalse(
            authorizes_deletion(
                "My surname is misspelled. Can you correct it without removing records?"
            )
        )

    def test_rejects_marketing_only_opt_out(self):
        self.assertFalse(
            authorizes_deletion(
                "Please remove me from marketing lists only. I still want receipts."
            )
        )


if __name__ == "__main__":
    unittest.main()
