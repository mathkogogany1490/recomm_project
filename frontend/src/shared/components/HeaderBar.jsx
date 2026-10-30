
import { Button, Space, Typography } from "antd";
import styled from "styled-components";

import { useAuth } from "../../auth/query/useAuth";

const Header = styled.header`
  height: 64px;
  padding: 0 24px;
  background: #ffffff;
  border-bottom: 1px solid #e8e8e8;

  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const Brand = styled(Typography.Text)`
  && {
    font-size: 19px;
    font-weight: 700;
    color: #1677ff;
  }
`;

export default function HeaderBar({
                                      onLogin,
                                      onRegister,
                                  }) {
    const { user, logout, isLoading } = useAuth();

    return (
        <Header>
            <Brand>추천 시스템 프로젝트</Brand>

            <Space>
                {user ? (
                    <>
                        <Typography.Text>
                            {user.email}
                        </Typography.Text>

                        <Button onClick={logout}>
                            로그아웃
                        </Button>
                    </>
                ) : (
                    <>
                        <Button
                            onClick={onLogin}
                            disabled={isLoading}
                        >
                            로그인
                        </Button>

                        <Button
                            type="primary"
                            onClick={onRegister}
                            disabled={isLoading}
                        >
                            회원가입
                        </Button>
                    </>
                )}
            </Space>
        </Header>
    );
}
