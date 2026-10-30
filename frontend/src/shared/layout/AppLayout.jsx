import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Card, Spin, Typography } from "antd";
import styled from "styled-components";

import HeaderBar from "../components/HeaderBar";
import SideBar from "../components/SideBar";

import LoginModal from "../../auth/components/LoginModal";
import RegisterModal from "../../auth/components/RegisterModal";
import { useAuth } from "../../auth/query/useAuth";

const Body = styled.div`
  display: flex;
  min-height: calc(100vh - 64px);
`;

const Main = styled.main`
  flex: 1;
  padding: 32px;
  background: #f5f7fb;
  min-width: 0;
`;

const Gate = styled.div`
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: #f5f7fb;
`;

export default function AppLayout() {
    const [loginOpen, setLoginOpen] = useState(false);
    const [registerOpen, setRegisterOpen] = useState(false);
    const { isAuthenticated, isLoading } = useAuth();

    return (
        <>
            <HeaderBar
                onLogin={() => setLoginOpen(true)}
                onRegister={() => setRegisterOpen(true)}
            />

            {isAuthenticated ? (
                <Body>
                    <SideBar />

                    <Main>
                        <Outlet />
                    </Main>
                </Body>
            ) : (
                <Gate>
                    <Card
                        style={{
                            width: 420,
                            textAlign: "center",
                        }}
                    >
                        {isLoading ? (
                            <Spin description="로그인 확인 중" />
                        ) : (
                            <>
                                <Typography.Title level={4}>
                                    로그인이 필요합니다
                                </Typography.Title>

                                <Typography.Paragraph type="secondary">
                                    회원, SVD, MF, Transformer 화면은
                                    로그인한 뒤에 열립니다.
                                </Typography.Paragraph>
                            </>
                        )}
                    </Card>
                </Gate>
            )}

            <LoginModal
                open={loginOpen}
                onClose={() => setLoginOpen(false)}
            />

            <RegisterModal
                open={registerOpen}
                onClose={() => setRegisterOpen(false)}
            />
        </>
    );
}