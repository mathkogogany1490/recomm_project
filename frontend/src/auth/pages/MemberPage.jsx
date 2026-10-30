
import {
    Alert,
    Card,
    Descriptions,
    Result,
    Spin,
    Typography,
} from "antd";

import { useAuth } from "../query/useAuth";
import { getApiError } from "../../shared/api/http";

export default function MemberPage() {
    const {
        user,
        isLoading,
        isAuthenticated,
        meQuery,
    } = useAuth();

    if (isLoading) {
        return (
            <Card>
                <Spin description="회원 정보를 확인하고 있습니다." />
            </Card>
        );
    }

    if (meQuery.isError) {
        return (
            <Alert
                type="error"
                showIcon
                message="회원 정보 조회 실패"
                description={getApiError(meQuery.error)}
            />
        );
    }

    if (!isAuthenticated) {
        return (
            <Card>
                <Result
                    status="info"
                    title="추천 시스템 프로젝트"
                    subTitle="로그인 또는 회원가입 후 이용할 수 있습니다."
                />
            </Card>
        );
    }

    return (
        <Card>
            <Typography.Title level={3}>
                회원 정보
            </Typography.Title>

            <Descriptions bordered column={1}>
                <Descriptions.Item label="회원 ID">
                    {user.id}
                </Descriptions.Item>

                <Descriptions.Item label="이메일">
                    {user.email}
                </Descriptions.Item>

                <Descriptions.Item label="이메일 인증">
                    {user.is_verified ? "인증 완료" : "미인증"}
                </Descriptions.Item>

                <Descriptions.Item label="가입일">
                    {user.created_at
                        ? new Date(user.created_at).toLocaleString("ko-KR")
                        : "-"}
                </Descriptions.Item>
            </Descriptions>
        </Card>
    );
}
