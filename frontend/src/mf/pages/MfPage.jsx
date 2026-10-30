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

import MfKpi from "../components/MfKpi";

import MfRecommendations from "../components/MfRecommendations";


const Page = styled.div`
    max-width: 1100px;
    margin: 0 auto;
`;

const Section = styled.div`
    margin-top: 24px;
`;


export default function MfPage() {
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
                MF 영화 추천
            </Typography.Title>

            <Typography.Paragraph
                type="secondary"
            >
                딥러닝 행렬 분해를 이용한
                고객별 영화 추천 시스템
            </Typography.Paragraph>

            <MfKpi />

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
                <MfRecommendations
                    userId={selectedUserId}
                />
            </Section>
        </Page>
    );
}