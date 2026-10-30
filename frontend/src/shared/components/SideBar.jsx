
import {
    UserOutlined,
    DatabaseOutlined,
    ApartmentOutlined,
    RobotOutlined,
} from "@ant-design/icons";

import { Menu } from "antd";
import { useLocation, useNavigate } from "react-router-dom";
import styled from "styled-components";

const SidebarContainer = styled.aside`
  width: 230px;
  min-height: calc(100vh - 64px);
  background: #ffffff;
  border-right: 1px solid #e8e8e8;
  padding-top: 16px;
  flex-shrink: 0;
`;

const items = [
    {
        key: "/member",
        icon: <UserOutlined />,
        label: "회원",
    },
    {
        key: "/svd",
        icon: <DatabaseOutlined />,
        label: "SVD 추천",
    },
    {
        key: "/mf",
        icon: <ApartmentOutlined />,
        label: "MF 추천",
    },
    {
        key: "/transformer",
        icon: <RobotOutlined />,
        label: "Transformer 추천",
        disabled: true,
    },
];

export default function SideBar() {
    const navigate = useNavigate();
    const location = useLocation();

    return (
        <SidebarContainer>
            <Menu
                mode="inline"
                selectedKeys={[location.pathname]}
                items={items}
                onClick={({ key }) => navigate(key)}
            />
        </SidebarContainer>
    );
}
