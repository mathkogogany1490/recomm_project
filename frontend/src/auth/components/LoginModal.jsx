
import { Alert, Button, Form, Input, Modal } from "antd";
import { useState } from "react";

import { useAuth } from "../query/useAuth";
import { getApiError } from "../../shared/api/http";

export default function LoginModal({
                                       open,
                                       onClose,
                                   }) {
    const [error, setError] = useState("");
    const { loginMutation } = useAuth();

    async function handleSubmit(values) {
        setError("");

        try {
            await loginMutation.mutateAsync(values);
            onClose();
        } catch (err) {
            setError(getApiError(err));
        }
    }

    return (
        <Modal
            title="로그인"
            open={open}
            onCancel={onClose}
            footer={null}
            destroyOnHidden
            afterClose={() => setError("")}
        >
            {error && (
                <Alert
                    type="error"
                    showIcon
                    message={error}
                    style={{ marginBottom: 16 }}
                />
            )}

            <Form
                layout="vertical"
                onFinish={handleSubmit}
                autoComplete="off"
            >
                <Form.Item
                    name="email"
                    label="이메일"
                    rules={[
                        { required: true, message: "이메일을 입력하세요." },
                        { type: "email", message: "이메일 형식을 확인하세요." },
                    ]}
                >
                    <Input placeholder="email@gmail.com" />
                </Form.Item>

                <Form.Item
                    name="password"
                    label="비밀번호"
                    rules={[
                        { required: true, message: "비밀번호를 입력하세요." },
                    ]}
                >
                    <Input.Password placeholder="비밀번호" />
                </Form.Item>

                <Button
                    type="primary"
                    htmlType="submit"
                    block
                    loading={loginMutation.isPending}
                >
                    로그인
                </Button>
            </Form>
        </Modal>
    );
}
