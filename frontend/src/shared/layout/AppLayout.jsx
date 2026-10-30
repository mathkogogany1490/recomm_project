
import { useState } from "react";
import { Outlet } from "react-router-dom";
import styled from "styled-components";

import HeaderBar from "../components/HeaderBar";
import SideBar from "../components/SideBar";

import LoginModal from "../../auth/components/LoginModal";
import RegisterModal from "../../auth/components/RegisterModal";

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

export default function AppLayout() {
    const [loginOpen, setLoginOpen] = useState(false);
    const [registerOpen, setRegisterOpen] = useState(false);

    return (
        <>
            <HeaderBar
                onLogin={() => setLoginOpen(true)}
                onRegister={() => setRegisterOpen(true)}
            />

            <Body>
                <SideBar />

                <Main>
                    <Outlet />
                </Main>
            </Body>

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
