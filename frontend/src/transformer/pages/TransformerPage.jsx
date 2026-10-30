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

import TransformerKpi from "../components/TransformerKpi";

import TransformerRecommendations from "../components/TransformerRecommendations";


const Page = styled.div`
    max-width: 1100px;
    margin: 0 auto;
`;

const Section = styled.div`
    margin-top: 24px;
`;


export default function TransformerPage() {
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
                Transformer 영화 추천
            </Typography.Title>

            <Typography.Paragraph
                type="secondary"
            >
                관측된 평점만으로 다음 평점을 예측하는
                고객별 영화 추천 시스템
            </Typography.Paragraph>

            <TransformerKpi />

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
                <TransformerRecommendations
                    userId={selectedUserId}
                />
            </Section>
        </Page>
    );
}