# transfer-1118f: 구현 기준 정정표·리뷰 반영 (#69, #78)

승인된 #67·#70·#71·#72·#73·#84는 건드리지 않는다(push하면 승인이 풀림).

| PR | 브랜치 | 지금 head(base) | 패치 | 적용 뒤 tree |
|---|---|---|---|---|
| #69 | feature/64-f1-rating-api | 17153c1cb9d39cd0b914191a74ecf4c7ed47923b | pr69-kmdb-rating.patch | 5d2a39a985666ba1aa0c87eaa6ed86ad64885d2d |
| #78 | feature/66-ai-eval-set | 32b1f04c6c9bcc1a8208c889f918ea3ca204e239 | pr78-eval-f3.patch | 7741855dea1d761a6c446aa173db1404f5ce4af7 |

순서
1. `sha256sum -c SHA256SUMS`
2. 각 브랜치를 head에서 `git checkout -B <브랜치> <head>` → `git am <패치>` → `git rev-parse HEAD^{tree}`가 표의 tree와 같은지 확인 → `git push origin <브랜치>`(강제 push 아님)
3. #69 제목은 `pr-69-title.txt`, 본문은 `pr-69-body.md`. #78 본문은 `pr-78-body.md`(제목 그대로)
4. 이슈 #64 본문 `issue-64-body.md`, 이슈 #66 본문 `issue-66-body.md`
5. #69·#78에 me-kyjun 리뷰 다시 요청
