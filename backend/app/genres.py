GENRE_KO = {
    "Action": "액션",
    "Adventure": "모험",
    "Animation": "애니메이션",
    "Children's": "아동",
    "Children": "아동",
    "Comedy": "코미디",
    "Crime": "범죄",
    "Documentary": "다큐멘터리",
    "Drama": "드라마",
    "Fantasy": "판타지",
    "Film-Noir": "필름 누아르",
    "Horror": "공포",
    "Musical": "뮤지컬",
    "Mystery": "미스터리",
    "Romance": "로맨스",
    "Sci-Fi": "SF",
    "Thriller": "스릴러",
    "War": "전쟁",
    "Western": "서부",
    "IMAX": "아이맥스",
    "(no genres listed)": "장르 없음",
}


def to_korean_genres(genres: str) -> str:
    if not genres:
        return ""

    names = []

    for name in str(genres).split("|"):
        name = name.strip()

        if not name:
            continue

        names.append(GENRE_KO.get(name, name))

    return ", ".join(names)