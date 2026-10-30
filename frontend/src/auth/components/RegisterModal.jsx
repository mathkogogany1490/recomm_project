
import { useState } from "react";
import { Alert, Button, Form, Input, Modal, Result } from "antd";

import { useAuth } from "../query/useAuth";
import { getApiError } from "../../shared/api/http";
import EmailVerifyForm from "./EmailVerifyForm";

export default function RegisterModal({
                                          open,
                                          onClose,
                                      }) {
    const { registerMutation } = useAuth();

    const [step, setStep] = useState("register");
    const [email, setEmail] = useState("");
    const [timing, setTiming] = useState(null);
    const [error, setError] = useState("");

    function reset() {
        setStep("register");
        setEmail("");
        setTiming(null);
        setError("");
    }

    async function handleRegister(values) {
        setError("");

        try {
            const result = await registerMutation.mutateAsync(values);

            setEmail(values.email);
            setTiming(result);
            setStep("verify");
        } catch (err) {
            setError(getApiError(err));
        }
    }

    return (
        <Modal
            title="회원가입"
            open={open}
            onCancel={onClose}
            afterClose={reset}
            footer={null}
            destroyOnHidden
            width={480}
        >
            {step === "register" && (
                <>
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
                        onFinish={handleRegister}
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
                                { min: 8, message: "비밀번호는 8자 이상 입력하세요." },
                            ]}
                        >
                            <Input.Password placeholder="비밀번호" />
                        </Form.Item>

                        <Button
                            type="primary"
                            htmlType="submit"
                            block
                            loading={registerMutation.isPending}
                        >
                            가입하고 인증번호 받기
                        </Button>
                    </Form>
                </>
            )}

            {step === "verify" && (
                <EmailVerifyForm
                    email={email}
                    initialTiming={timing}
                    onVerified={() => setStep("complete")}
                />
            )}

            {step === "complete" && (
                <Result
                    status="success"
                    title="이메일 인증 완료"
                    subTitle="이제 로그인할 수 있습니다."
                    extra={
                        <Button type="primary" onClick={onClose}>
                            확인
                        </Button>
                    }
                />
            )}
        </Modal>
    );
}
