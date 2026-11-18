# transfer-1118g: #67·#70 병합 뒤 쌓인 PR을 main 기준으로 정리

stack.bundle에 아래 커밋이 들어 있다(main 합치기 + 정정표 번호 주석). 커밋 sha가 그대로 전달된다.

| PR | 브랜치 | 지금 head | 새 head(bundle) | base |
|---|---|---|---|---|
| #72 | feature/65-f4-dictionary | b4c0f00c93a8a3b98c494b8a7a55388549f880c5 | 1f0ca257e23b94a99bbbfbf97529c900b70e55d6 (r-72) | main(이미 바뀜) |
| #73 | feature/65-f4-search-templates | 98697b806deb5e0211643645a753dc213ba06e74 | 3211e7eeb6dc236f45cc089e88cd95aac4eddbfe (r-73) | main으로 |
| #71 | feature/26-c1-batch-entry | 2901d99df997943dd393a3bb536c89833335112b | a6bc80ad31a54952a4acf0019a4ed31684dff35b (r-71) | main으로 |
| #84 | feature/83-c1-station-time | af7e7124915288e74f7dfcc54c67140d7bfe2ba9 | d3dd448ece39d46154d19283b8a4b9e74ef97dcc (r-84) | main으로 |
| #69 | feature/64-f1-rating-api | 6f34b0c9c03ed9b6cd64d494eef6706903df72cd | 6d8a8242efd0ff5c46f28f907a8772d848a11d00 (r-69) | main으로 |

새 head는 모두 지금 head의 자손이라 일반 push(fast-forward)로 된다. main은 014362d.

순서
1. `sha256sum -c SHA256SUMS`, `git fetch origin`, `git bundle verify stack.bundle`
2. `git fetch stack.bundle 'refs/heads/r-*:refs/remotes/bundle/r-*'` → 각 sha가 표와 같은지 확인
3. PR마다: 지금 head가 표와 같은지 확인 → base를 main으로(`gh pr edit N --base main`) → `git push origin <새 sha>:refs/heads/<브랜치>`(강제 push 금지). base를 먼저 바꿔야 CI가 main 대상으로 돈다
4. 제목·본문: pr-72/73/84-title.txt, pr-69/71/72/73/84-body.md
5. 이슈 #65 제목·본문(issue-65-*), 이슈 #83 제목·본문(issue-83-*). F4 라벨이 있고 F3 라벨이 저장소에 있으면 #65·#72·#73의 F4 라벨을 F3로
6. #72·#73·#71·#84·#69에 me-kyjun 리뷰 요청
