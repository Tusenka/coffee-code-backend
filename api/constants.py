SWAGGER_USER_PROFILE_EXAMPLE = {
    "user": {
        "id": "5c9a777c-2b9e-47e1-8996-fed108c93769",
        "email": "ourtusenka@yandex.ru",
        "first_name": "alex",
        "last_name": "anonym",
        "bio": "bio",
        "created_at": "2025-12-16T14:23:06.495237",
        "photo_urls": "",
        "telegram_username": "irina_tusenka",
    },
    "country": "Russia",
    "city_name": "Moscow",
    "timezone": "Europe/Moscow",
    "skills": [
        {"id": "2", "name": "python"},
        {"id": "3", "value": "C++"},
    ],
    "mentor_skills": [{"id": "4", "name": "python"}],
    "mentee_skills": [{"id": "1", "name": "transformers"}],
    "goals": [{"id": "1", "name": "brainstorm"}],
    "complete": "False",
}

SWAGGER_SKILLS_EXAMPLE = {
    "Языки программирования": [
        {
            "id": "1",
            "value": "JS",
            "weight": "10",
        },
        {
            "id": "2",
            "value": "C++",
            "weight": "9",
        },
        {
            "id": "3",
            "value": "Python",
            "weight": "10",
        },
        {
            "id": "4",
            "value": "Rust",
            "weight": "8",
        },
    ],
    "Фреймворки": [
        {
            "id": "5",
            "value": "Nextjs",
            "weight": "10",
        },
        {
            "id": "6",
            "value": "Pytest",
            "weight": "9",
        },
        {
            "id": "7",
            "value": "Transformers",
            "weight": "10",
        },
    ],
    "Общее": [
        {
            "id": "8",
            "value": "ML",
            "weight": "10",
        },
        {
            "id": "9",
            "value": "Math",
            "weight": "9",
        },
        {
            "id": "10",
            "value": "Hackathons",
            "weight": "8",
        },
    ],
    "Образ жизни": [
        {
            "id": "5",
            "value": "Спорт",
            "weight": "10",
        },
        {
            "id": "6",
            "value": "Рыбалкa",
            "weight": "10",
        },
        {
            "id": "7",
            "value": "Походы",
            "weight": "10",
        },
    ],
    "Финансы": [
        {
            "id": "8",
            "value": "Криптовалюта",
            "weight": "10",
        },
        {
            "id": "9",
            "value": "Инвестиии",
            "weight": "10",
        },
        {
            "id": "10",
            "value": "Стартапы",
            "weight": "10",
        },
    ],
    "Изучение": [
        {
            "id": "8",
            "value": "Иностранные языкы",
            "weight": "10",
        },
        {
            "id": "9",
            "value": "Вокал",
            "weight": "10",
        },
        {
            "id": "10",
            "value": "Биология",
            "weight": "10",
        },
    ],
}
SWAGGER_GOALS_EXAMPLE = {
    "goals": [
        {
            "id": "5",
            "value": "Брейншторм",
        },
        {
            "id": "6",
            "value": "Стартапы",
        },
        {
            "id": "7",
            "value": "Инвестиции",
        },
        {
            "id": "8",
            "value": "Деловые контакты",
        },
    ],
}

SWAGGER_UNAUTHORIZED_EXAMPLE = {"error": "Вы не выполнили вход."}
SWAGGER_OK_EXAMPLE = {"message": "Данные пользователя изменены."}
