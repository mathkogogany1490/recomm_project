
import {
    useState,
} from "react";

import {
    Button,
    Card,
    InputNumber,
    Space,
    Typography,
} from "antd";

import styled from "styled-components";

import MseKpi from "../components/MseKpi";

import RecommendationTable from "../components/RecommendationTable";


const Page = styled.div`
    max-width: 1100px;
    margin: 0 auto;
`;

const Section = styled.div`
    margin-top: 24px;
`;


export default function SvdPage() {
    const [
        inputUserId,
        setInputUserId,
    ] = useState(null);

    const [
        selectedUserId,
        setSelectedUserId,
    ] = useState(null);


    function handleSearch() {
        if (
            !Number.isInteger(inputUserId) ||
            inputUserId < 1
        ) {
            return;
        }

        setSelectedUserId(
            inputUserId
        );
    }


    return (
        <Page>
            <Typography.Title
                level={2}
            >
                SVD 영화 추천
            </Typography.Title>

            <Typography.Paragraph
                type="secondary"
            >
                희소 행렬 SVD를 이용한
                고객별 영화 추천 시스템
            </Typography.Paragraph>

            <MseKpi />

            <Section>
                <Card title="고객 선택">
                    <Space wrap>
                        <InputNumber
                            min={1}
                            precision={0}
                            placeholder="고객 아이디"
                            value={inputUserId}
                            onChange={setInputUserId}
                            style={{
                                width: 220,
                            }}
                            onPressEnter={handleSearch}
                        />

                        <Button
                            type="primary"
                            onClick={handleSearch}
                            disabled={
                                !Number.isInteger(
                                    inputUserId
                                ) ||
                                inputUserId < 1
                            }
                        >
                            추천 조회
                        </Button>
                    </Space>
                </Card>
            </Section>

            <Section>
                <RecommendationTable
                    userId={selectedUserId}
                />
            </Section>
        </Page>
    );
}
