import {
    Alert,
    Card,
    Empty,
    Spin,
    Table,
    Tag,
} from "antd";

import {
    useTransformerRecommendations,
} from "../query/useTransformer";

import {
    getApiError,
} from "../../shared/api/http";


const columns = [
    {
        title: "순위",
        dataIndex: "rank",
        key: "rank",
        width: 90,
        align: "center",
        render: (rank) => (
            <Tag
                color={
                    rank === 1
                        ? "gold"
                        : "blue"
                }
            >
                {rank}위
            </Tag>
        ),
    },
    {
        title: "영화 ID",
        dataIndex: "movie_id",
        key: "movie_id",
        width: 110,
    },
    {
        title: "영화 제목",
        dataIndex: "title",
        key: "title",
    },
    {
        title: "장르",
        dataIndex: "genres",
        key: "genres",
    },
    {
        title: "예측 평점",
        dataIndex: "predicted_rating",
        key: "predicted_rating",
        width: 130,
        align: "right",
        render: (value) =>
            Number(value).toFixed(4),
    },
];


export default function TransformerRecommendations({
    userId,
}) {
    const {
        data,
        isPending,
        isError,
        error,
    } = useTransformerRecommendations(
        userId
    );

    if (!userId) {
        return (
            <Card title="추천 영화 TOP 5">
                <Empty
                    description="고객 아이디를 입력하세요."
                />
            </Card>
        );
    }

    if (isPending) {
        return (
            <Card title="추천 영화 TOP 5">
                <Spin
                    description="추천 영화를 조회하고 있습니다."
                />
            </Card>
        );
    }

    if (isError) {
        return (
            <Alert
                type="error"
                showIcon
                title="영화 추천 조회 실패"
                description={getApiError(error)}
            />
        );
    }

    return (
        <Card
            title={`고객 ${userId} — 추천 영화 TOP 5`}
        >
            <Table
                rowKey="movie_id"
                columns={columns}
                dataSource={
                    data?.recommendations ?? []
                }
                pagination={false}
                size="middle"
                locale={{
                    emptyText:
                        "추천할 영화가 없습니다.",
                }}
            />
        </Card>
    );
}