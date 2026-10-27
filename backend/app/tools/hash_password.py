"""관리자 비밀번호 argon2 해시 만들기: python -m app.tools.hash_password

비밀번호는 화면에 보이지 않게 입력받고, 출력한 해시만 .env의 ADMIN_PASSWORD_HASH에 넣는다.
"""

from getpass import getpass

from argon2 import PasswordHasher


def main() -> None:
    pw = getpass("관리자 비밀번호: ")
    if len(pw) < 12 or pw != getpass("한 번 더: "):
        raise SystemExit("12자 이상, 두 번 같게 입력해 주세요")
    print(PasswordHasher().hash(pw))


if __name__ == "__main__":
    main()
