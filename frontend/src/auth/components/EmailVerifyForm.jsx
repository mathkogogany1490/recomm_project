
import { useEffect, useState } from "react";
import {
    Alert,
    Button,
    Form,
    Input,
    Space,
    Typography,
} from "antd";

import { useAuth } from "../query/useAuth";
import { getApiError } from "../../shared/api/http";

function getSeconds(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
        return null;
    }

    return Math.max(0, Math.floor(value));
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remaining = seconds % 60;

    return `${String(minutes).padStart(2, "0")}:${String(
        remaining
    ).padStart(2, "0")}`;
}

export default function EmailVerifyForm({
                                            email,
                                            initialTiming,
                                            onVerified,
                                        }) {
    const { verifyMutation, resendMutation } = useAuth();

    const [form] = Form.useForm();
    const [error, setError] = useState("");

    const [expiresAt, setExpiresAt] = useState(null);
    const [resendAt, setResendAt] = useState(null);
    const [now, setNow] = useState(Date.now());

    function applyTiming(data) {
        const current = Date.now();

        const expiresIn = getSeconds(data?.expires_in);
        const resendAfter = getSeconds(data?.resend_after);

        setExpiresAt(
            expiresIn === null ? null : current + expiresIn * 1000
        );

        setResendAt(
            resendAfter === null ? null : current + resendAfter * 1000
        );

        setNow(current);
    }

    useEffect(() => {
        applyTiming(initialTiming);
    }, [initialTiming]);

    useEffect(() => {
        const interval = setInterval(() => {
            setNow(Date.now());
        }, 1000);

        return () => clearInterval(interval);
    }, []);

    const remaining =
        expiresAt === null
            ? null
            : Math.max(0, Math.ceil((expiresAt - now) / 1000));

    const resendRemaining =
        resendAt === null
            ? 0
            : Math.max(0, Math.ceil((resendAt - now) / 1000));

    const expired = remaining === 0;

    async function handleVerify(values) {
        setError("");

        if (expired) {
            setError("인증번호가 만료되었습니다. 다시 보내기를 이용하세요.");
            return;
        }

        try {
            await verifyMutation.mutateAsync({
                email,
                code: values.code,
            });

            onVerified();
        } catch (err) {
            setError(getApiError(err));
        }
    }

    async function handleResend() {
        setError("");

        try {
            const result = await resendMutation.mutateAsync(email);

            applyTiming(result);
            form.resetFields();
        } catch (err) {
            setError(getApiError(err));
        }
    }

    return (
        <div>
            <Typography.Paragraph>
                <strong>{email}</strong> 주소로 발송한
                6자리 인증번호를 입력하세요.
            </Typography.Paragraph>

            <div style={{ textAlign: "center", marginBottom: 16 }}>
                <Typography.Title
                    level={2}
                    style={{
                        margin: 0,
                        color: expired ? "#cf1322" : "#1677ff",
                    }}
                >
                    {remaining === null ? "--:--" : formatTime(remaining)}
                </Typography.Title>

                {remaining === null && (
                    <Typography.Text type="secondary">
                        서버에서 인증번호 만료 시간을 받지 못했습니다.
                    </Typography.Text>
                )}
            </div>

            {error && (
                <Alert
                    type="error"
                    showIcon
                    message={error}
                    style={{ marginBottom: 16 }}
                />
            )}

            {expired && (
                <Alert
                    type="warning"
                    showIcon
                    message="인증번호가 만료되었습니다."
                    style={{ marginBottom: 16 }}
                />
            )}

            <Form
                form={form}
                layout="vertical"
                onFinish={handleVerify}
            >
                <Form.Item
                    label="인증번호"
                    name="code"
                    rules={[
                        { required: true, message: "인증번호를 입력하세요." },
                        {
                            pattern: /^\d{6}$/,
                            message: "숫자 6자리를 입력하세요.",
                        },
                    ]}
                >
                    <Input
                        maxLength={6}
                        inputMode="numeric"
                        placeholder="6자리 인증번호"
                        size="large"
                        disabled={expired}
                    />
                </Form.Item>

                <Button
                    type="primary"
                    htmlType="submit"
                    block
                    disabled={expired}
                    loading={verifyMutation.isPending}
                >
                    이메일 인증
                </Button>
            </Form>

            <Space
                direction="vertical"
                style={{ width: "100%", marginTop: 16 }}
            >
                <Button
                    block
                    disabled={resendRemaining > 0}
                    loading={resendMutation.isPending}
                    onClick={handleResend}
                >
                    {resendRemaining > 0
                        ? `다시 보내기 (${formatTime(resendRemaining)})`
                        : "인증번호 다시 보내기"}
                </Button>
            </Space>
        </div>
    );
}
