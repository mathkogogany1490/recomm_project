import {
    Alert,
    Card,
    Col,
    Row,
    Skeleton,
    Statistic,
    Typography,
} from "antd";

import {
    useMfKpi,
} from "../query/useMf";

import {
    getApiError,
} from "../../shared/api/http";


export default function MfKpi() {
    const {
        data,
        isPending,
        isError,
        error,
    } = useMfKpi();

    if (isPending) {
        return (
            <Card>
                <Skeleton active />
            </Card>
        );
    }

    if (isError) {
        return (
            <Alert
                type="error"
                showIcon
                title="MF KPI 조회 실패"
                description={getApiError(error)}
            />
        );
    }

    return (
        <>
            <Row gutter={[16, 16]}>
                <Col xs={24} md={8}>
                    <Card>
                        <Statistic
                            title="평균 절대 오차 (MAE)"
                            value={data.mae}
                            precision={6}
                            valueStyle={{
                                color: "#1677ff",
                                fontWeight: 700,
                            }}
                        />

                        <Typography.Text
                            type="secondary"
                        >
                            실제 평점과 예측 평점의
                            절대 차이 평균
                        </Typography.Text>
                    </Card>
                </Col>

                <Col xs={24} md={8}>
                    <Card>
                        <Statistic
                            title="평균 제곱 오차 (MSE)"
                            value={data.mse}
                            precision={6}
                            valueStyle={{
                                color: "#cf1322",
                                fontWeight: 700,
                            }}
                        />

                        <Typography.Text
                            type="secondary"
                        >
                            평점 오차 제곱의 평균
                        </Typography.Text>
                    </Card>
                </Col>

                <Col xs={24} md={8}>
                    <Card>
                        <Statistic
                            title="평균 제곱근 오차 (RMSE)"
                            value={data.rmse}
                            precision={6}
                            valueStyle={{
                                color: "#389e0d",
                                fontWeight: 700,
                            }}
                        />

                        <Typography.Text
                            type="secondary"
                        >
                            제곱 오차를 평점 단위로 환산
                        </Typography.Text>
                    </Card>
                </Col>
            </Row>

            <Card
                style={{
                    marginTop: 16,
                }}
            >
                <Typography.Text
                    type="secondary"
                >
                    고객{" "}
                    {data.user_count.toLocaleString()}
                    명
                    {" · "}
                    영화{" "}
                    {data.movie_count.toLocaleString()}
                    편
                    {" · "}
                    평점{" "}
                    {data.rating_count.toLocaleString()}
                    건
                    {" · "}
                    잠재요인 {data.factors}개
                </Typography.Text>

                <div style={{ marginTop: 8 }}>
                    <Typography.Text
                        type="secondary"
                    >
                        평가 기준: 학습 데이터의
                        관측 평점
                    </Typography.Text>
                </div>
            </Card>
        </>
    );
}