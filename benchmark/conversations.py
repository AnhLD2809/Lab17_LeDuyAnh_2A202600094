"""
10 multi-turn conversations dùng để benchmark agent có/không có memory.

Bao phủ 5 nhóm test theo rubric:
  - profile_recall
  - conflict_update
  - episodic
  - semantic
  - token_budget
"""

TEST_CONVERSATIONS = [
    {
        "id": 1,
        "topic": "Language Preference + Project Scoping",
        "category": "profile_recall",
        "turns": [
            "Tôi thích Python và ghét Java. Tôi đang học lập trình được 6 tháng.",
            "Tôi muốn xây dựng một web scraper thu thập giá sản phẩm từ nhiều trang e-commerce.",
            "Nên dùng BeautifulSoup hay Scrapy cho dự án này? Tại sao?",
            "Tôi bị blocked bởi Cloudflare anti-bot khi scrape. Làm thế nào để bypass?",
            "Sau khi lấy được dữ liệu, tôi nên lưu vào đâu để query nhanh sau này?",
            "Dựa trên preference của tôi, stack tổng thể bạn khuyên tôi cho toàn bộ dự án là gì?",
        ],
    },
    {
        "id": 2,
        "topic": "Allergy Conflict Update + Meal Planning",
        "category": "conflict_update",
        "turns": [
            "Tôi tên là Linh. Tôi dị ứng sữa bò nên cần tránh các thực phẩm có sữa.",
            "Bạn có thể gợi ý thực đơn bữa sáng không có sữa bò không?",
            "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò. Xin lỗi vì đã nhầm.",
            "Vậy giờ bạn có thể điều chỉnh lại thực đơn phù hợp với dị ứng đậu nành không?",
            "Ngoài dị ứng đậu nành, tôi còn muốn giảm cân. Thực đơn nên thay đổi thế nào?",
        ],
    },
    {
        "id": 3,
        "topic": "Episodic: Debug Journey",
        "category": "episodic",
        "turns": [
            "Tôi bị confused với async/await trong Python, không hiểu lắm tại sao cần dùng.",
            "Code của tôi raise RuntimeError: This event loop is already running trong Jupyter.",
            "Tôi đã fix được bằng nest_asyncio nhưng nay lại bị lỗi khác: Task was destroyed but it is pending.",
            "Nhớ lại lỗi trước tôi đã gặp, bạn nghĩ hai lỗi này có liên quan không?",
            "Vậy đâu là best practice để dùng asyncio trong Jupyter notebook mà không bị các lỗi này?",
        ],
    },
    {
        "id": 4,
        "topic": "Semantic: FastAPI Production Setup",
        "category": "semantic",
        "turns": [
            "FastAPI là gì và tại sao nó được coi là framework Python hiện đại?",
            "So với Django REST Framework, FastAPI có ưu/nhược điểm gì?",
            "Tôi cần implement JWT authentication trong FastAPI. Các bước thực hiện?",
            "Làm thế nào để setup rate limiting và bảo vệ API khỏi DDoS?",
            "Deployment production: nên dùng Uvicorn + Gunicorn hay Hypercorn? Config tối ưu?",
            "Bạn có thể tóm tắt toàn bộ production checklist cho một FastAPI app không?",
        ],
    },
    {
        "id": 5,
        "topic": "Token Budget: Long ML Pipeline",
        "category": "token_budget",
        "turns": [
            "Tôi muốn build model phân loại spam email từ đầu. Bắt đầu từ đâu?",
            "Dữ liệu của tôi bị imbalanced: 95% ham, 5% spam. Xử lý imbalanced data thế nào?",
            "Tôi đã thử SMOTE nhưng F1 vẫn thấp (0.72). Có kỹ thuật nào tốt hơn không?",
            "Nên dùng TF-IDF hay BERT embeddings cho text classification? Trade-off là gì?",
            "Sau khi train xong, làm thế nào để deploy model lên production mà không downtime?",
            "Monitoring model trong production: drift detection và retraining strategy ra sao?",
        ],
    },
    {
        "id": 6,
        "topic": "Semantic: Database & Caching",
        "category": "semantic",
        "turns": [
            "Tôi cần thiết kế schema cho social media với 10M users. Nên dùng SQL hay NoSQL?",
            "Bảng posts có 100M rows, query bị slow dù đã index. Nguyên nhân có thể là gì?",
            "Tôi đang dùng LIKE '%keyword%' để tìm kiếm, rất slow. Giải pháp thay thế?",
            "Caching strategy: Redis cache-aside vs write-through vs write-behind khác nhau thế nào?",
            "Làm thế nào để implement cursor-based pagination cho 100M rows một cách hiệu quả?",
        ],
    },
    {
        "id": 7,
        "topic": "Profile Recall: OOP & Design Patterns",
        "category": "profile_recall",
        "turns": [
            "Tôi là senior Python developer, đang refactor codebase 5000 dòng với toàn global variables.",
            "Khi nào dùng abstract class vs Protocol trong Python? Ví dụ cụ thể?",
            "Strategy pattern giúp gì trong trường hợp có 10 loại payment methods?",
            "Observer pattern vs event-driven architecture: khi nào dùng cái nào?",
            "Dependency Injection trong Python: có cần framework không, hay có thể tự implement?",
            "Dựa trên level của tôi, bạn có recommendation gì về learning path tiếp theo không?",
        ],
    },
    {
        "id": 8,
        "topic": "Token Budget: Microservices Architecture",
        "category": "token_budget",
        "turns": [
            "Tôi đang migrate monolith Python app sang microservices. Tiêu chí chia service?",
            "Làm thế nào để handle distributed transactions giữa các services?",
            "Service A -> B -> C: nếu C timeout, làm thế nào tránh cascade failure?",
            "Event sourcing với Kafka hay REST polling tốt hơn để đồng bộ data?",
            "Làm thế nào để implement API versioning mà không breaking backward compatibility?",
        ],
    },
    {
        "id": 9,
        "topic": "Episodic: Testing Journey",
        "category": "episodic",
        "turns": [
            "Tôi chưa có test nào trong dự án 2 năm tuổi. Chiến lược để bắt đầu?",
            "Tôi bị confused với mock vs patch trong pytest. Khi nào dùng cái nào?",
            "Nhớ lại vấn đề tôi đang gặp, làm thế nào để mock external API calls đúng cách?",
            "pytest-cov báo 45% coverage, target bao nhiêu là đủ và làm sao tăng?",
            "Setup GitHub Actions CI: test -> lint -> coverage -> deploy. Config cơ bản ra sao?",
            "Tôi cần test database queries. Dùng SQLite in-memory hay Docker service tốt hơn?",
        ],
    },
    {
        "id": 10,
        "topic": "Token Budget: Cloud Scale Architecture",
        "category": "token_budget",
        "turns": [
            "App Python của tôi cần scale lên 100k concurrent users. Architecture nào phù hợp?",
            "Docker vs Kubernetes: startup của tôi có 3 developers, K8s có đáng đầu tư không?",
            "Tôi muốn zero-downtime deployment. Blue-green vs canary: khác nhau chỗ nào?",
            "Làm thế nào để auto-scale dựa trên custom metrics (request queue length) trong K8s?",
            "Cost optimization: đang tốn $2000/tháng AWS, làm thế nào giảm 50%?",
            "Observability stack: Prometheus + Grafana + Jaeger setup trong Python app ra sao?",
        ],
    },
]
