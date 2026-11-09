-- BR-11 검수 범위(0.6 이상 0.9 미만) 후보. 반영할 때 review_item(kind='match')으로 옮긴다
ALTER TABLE stg.work ADD COLUMN match_candidate VARCHAR(20);
