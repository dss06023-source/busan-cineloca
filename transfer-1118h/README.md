# transfer-1118h: 쌓인 PR 정리본 (#72·#73·#69) + #84 번호 커밋

transfer-1118g를 대신한다(#71은 병합됨, #84는 김예준님이 main을 합친 c55a20a 위에 커밋 하나).

| PR | 브랜치 | 지금 head | 새 head(bundle) | base |
|---|---|---|---|---|
| #72 | feature/65-f4-dictionary | b4c0f00c93a8a3b98c494b8a7a55388549f880c5 | 1f0ca257e23b94a99bbbfbf97529c900b70e55d6 (r-72) | main(이미) |
| #73 | feature/65-f4-search-templates | 98697b806deb5e0211643645a753dc213ba06e74 | 3211e7eeb6dc236f45cc089e88cd95aac4eddbfe (r-73) | main으로 |
| #69 | feature/64-f1-rating-api | 6f34b0c9c03ed9b6cd64d494eef6706903df72cd | 6d8a8242efd0ff5c46f28f907a8772d848a11d00 (r-69) | main(이미) |
| #84 | feature/83-c1-station-time | c55a20af283156f3ff5cf990913e4fbe8485cd24 | acc7cc5fb0dd0c3847bec8627ad9a7a3d5375981 (r-84b) | main(이미) |

모두 fast-forward. 최신 main 92c7ed3과 충돌 없음, 합친 상태 pytest 536 passed.

순서: SHA256SUMS 확인 → bundle verify → `git fetch stack.bundle 'refs/heads/r-*:refs/remotes/bundle/r-*'` → head 확인 → (#73만) `gh pr edit 73 --base main` → 일반 push → 제목(pr-72/73/84-title.txt)·본문(pr-69/72/73/84-body.md) → 이슈 #65·#83 제목·본문 → F4 라벨이 있고 F3 라벨이 있으면 바꾸기 → #72·#73·#69·#84에 me-kyjun 리뷰 요청
